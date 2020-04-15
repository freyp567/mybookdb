"""
import from onleihe Merkzettel
see utils/extract_merkliste to generate input csv

"""

from datetime import datetime
from pathlib import Path
import csv

from django.utils import timezone
from django.db import IntegrityError, transaction
from django.core.management.base import BaseCommand, CommandError

from bookshelf.models import books, authors, comments, onleiheBooks, states
from bookmarks.models import book_links, linksites


class Command(BaseCommand):
    help = 'Imports book items from onleihe merkzettel'

    def add_arguments(self, parser):
        parser.add_argument('csv', type=Path)
        
    def handle(self, *args, **options):
        csv_path = options['csv']
        self.stdout.write(f"importing books form onleihe Merkliste using {csv_path}\n")
        assert csv_path.is_file(), "missing csv"
        #"D:\backup\onleihe_merkzettel\watchlist_onleihe.csv"
        watchlist, self.list_updated = self.load_watchlist(csv_path)
        for item in watchlist:
            self.import_watchlist_book(item)
        self.stdout.write("import finished.\n")
        
    def import_watchlist_book(self, item):
        # lookup book in bookshelf
        book_title = item['title']
        found = books.objects.filter(title=book_title)
        if not found:
            # TODO check for normalization issues
            self.stdout.write(f"not found: {book_title}\n")
            self.add_book(item)
        else:
            assert len(found) == 1, "title not unique: %s" % book_title
            self.update_book(found[0], item)

    def normalize_title(self, title):
        title = title.replace('\u00ac', '')
        # &#172;, NOT SIGN / angled dash - used to delimit optional title parts, e.g. ¬Der¬ Besucher
        return title
        
    def add_book(self, item):
        now = datetime.now(tz=timezone.utc)
        book_title = self.normalize_title(item['title'])
        with transaction.atomic():
            comment_obj = comments()
            comment_obj.bookTitle = book_title
            comment_obj.dateCreatedInt = int(now.timestamp() *1000)
            comment_obj.dateCreated = now
            comment_obj.text = "onleihe Merkzettel, %s %s %s" % (item['category'], item['media'], item['since'],)
            
            book_obj = books()
            comment_obj.book = book_obj
            
            book_obj.title = book_title
            book_obj.isbn13 = item['ISBN']
            book_obj.new_description = item.get('content')
            book_obj.publisher =item.get('publisher')
            books.publicationDate =item['year']
            book_obj.created = now
            book_obj.updated = now
    
            if ';' in item['author']:
                author_name = item['author'].split(';')
                if author_name[0] == author_name[1]:
                    author_name = author_name[0]
                else:
                    # what can be found:
                    # 'Brontë, Emily;Brontë, Emily' -- 'ë' vs 'e' / b'e&#776;'
                    # 'Mason, Daniel;Mason, Daniel Philippe'
                    # 'Rysopp, Beate;Mytting, Lars' -- audiostream, former is Sprecher
                    self.stdout.write(f"multiple authors, verify book '{book_title}': {author_name}\n")
                    author_name = author_name[1]
                    # TODO examine                    
            else:
                author_name =item['author']
                
            if author_name:                
                author_parts = [p.strip() for p in author_name.split(',')]
                author_name = "%s %s" % (" ".join(author_parts[1:]), author_parts[0])
            else:
                self.stdout.write(f"book without author: {book_obj.title}")
                author_name = "Autor unbekannt"
                author_parts = ['unbekannt', 'Autor']
            
            author_found = authors.objects.filter(name=author_name)
            if not author_found:
                author_found = authors.objects.filter(name=item['author'])
                
            if not author_found:
                author_found = authors.objects.filter(familyName=author_parts[0])
                assert not author_found, 'verify %s' % author_name
                
            if not author_found:
                # authors.objects.filter(name__icontains = xxx)
                author_obj = authors()
                author_obj.name = author_name
                author_obj.lowerCaseName = author_name.lower()
                author_obj.familyName = author_parts[0]
                author_obj.updated = now
            else:
                assert len(author_found) == 1, "author name not unique:%s" % author_name
                author_obj = author_found[0]
                
            
            # href  TODO add to book_obj.book_links
            
            author_obj.save()
            book_obj.save()
            comment_obj.save()            
            book_obj.authors.add(author_obj)
    
            link_obj = self.create_book_link(book_obj, item)
    
            states_obj = states(pk=book_obj.id)
            states_obj.book = book_obj
            states_obj.toRead = True
            states_obj.toBuy = True  # == on wishlist
            states_obj.save()
    
            onleihe_book = onleiheBooks(
                book=book_obj,
                onleiheId = item['href'],
                status = 'wishlist',
                updated = now,
                )
            onleihe_book.save()
        
    def update_book(self, book_obj, item):
        book_states = states.objects.filter(book_id = book_obj.id)
        assert len(book_states) == 1, "troubles with state for book %s" % book_obj
        book_states = book_states[0]
        if book_states.haveRead or book_states.readingNow:
            raise ValueError("book from Merkliste but state %s" % book_obj.state_info)
        if not book_states.toBuy:
            #raise ValueError("book from Merkliste, bad state %s" % book_obj.state_info
            self.stdout.write(f"not on wishlist / toBuy not set: {book_obj.title} id={book_obj.id} -- corrected\n")
        book_states.toBuy = True                             
        book_states.save()
        
        # compare book properties, and update if neccessary
        # currently updating only link to onleihe 

        if book_obj.new_description != item.get('content'):
            book_obj.new_description = item['content']

        with transaction.atomic():        
            # add link to onleihe
            have_link = None
            for link_obj in book_obj.book_links.all():
                if link_obj.link_uri == item['href']:
                    have_link = link_obj
                    break
    
            if not have_link:
                link_obj = self.create_book_link(book_obj, item)
        
        return
    
    def get_link_name(self, uri):
        if not uri:
            return 'onleihe'
        steps = uri.split('/')
        # 'mediaInfo,0-0-1198403364-200-0-0-0-0-0-0-0.html'
        # see get_linkname_from_path
        onleihe_id = steps[-1].split(',')[1][:-5]
        while onleihe_id.endswith('-0'):
            onleihe_id = onleihe_id[:-2]
        return 'onleihe-%s' % onleihe_id

    def create_book_link(self, book_obj, item):
          now = datetime.now(tz=timezone.utc)
          
          site_obj = linksites.objects.filter(name='onleihe.de/wishlist')
          if not site_obj:
              # create site onleihe (variant wishlist)
              site_obj = linksites()
              site_obj.name = 'onleihe.de/wishlist'
              site_obj.description = "onleihe wishlist (Merkzettel)"
              site_obj.base_url = 'http://www4.onleihe.de'
              site_obj.save()
          else:
              site_obj = site_obj.first()
              
          link_obj = book_links()
          link_obj.name = 'www4.onleihe.de'
          link_obj.link_name = self.get_link_name(item['href'])
          link_obj.link_site = site_obj.id
          link_obj.link_uri = item['href']
          link_obj.link_state = 'wishlist'
          link_obj.created = now
          link_obj.updated = now
          link_obj.verified = self.list_updated
          link_obj.book = book_obj
          link_obj.save()
          
          book_obj.book_links.add(link_obj)
          book_obj.updated = now
          book_obj.save()
        
    def load_watchlist(self, csv_path):
        items = []
        modified = datetime.fromtimestamp(csv_path.stat().st_mtime)
        with csv_path.open('r', encoding='utf-8-sig') as csv_file:
            # latin-1 -> UnicodeEncodeError: 'latin-1' codec can't encode character '\u0308' in position 69: ordinal not in range(256)
            reader =  csv.DictReader(csv_file, restkey="extra", restval="", dialect="excel")
            row_count = 0
            for row in reader:
                row = dict(row)
                row_count += 1
                assert not row.get("extra")
                items.append(row)
        return items, modified

