# -*- coding: latin-1 -*-
"""
sync mybookdb with information from Book Catalogue export.csv

"""

import os
import sys
from pathlib import Path
import csv
from datetime import datetime
from decimal import Decimal
import uuid
import difflib
import isbnlib
from isbnlib.dev._exceptions import DataNotFoundAtServiceError

from pyisbn import Isbn13

from django.db import transaction
from django.core.management.base import BaseCommand
from django.utils import timezone

from bookshelf.models import books, authors, comments, states

import logging 
LOG_FORMAT = "%(levelname)-8s %(message)s"
LOG_FORMAT_EX = "%(asctime)-15s %(levelname)-8s %(message)s"  # for file logging
LOG_DATE_FORMAT = "%m-%dT%H:%M:%S"
LOGLEVEL = os.environ.get('LOGLEVEL') or logging.INFO
logging.basicConfig(stream=sys.stdout, level=LOGLEVEL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
#logging.basicConfig()
for logname in ('', 'django.db.backends'):
    logging.getLogger(logname).setLevel('INFO')
LOGGER = logging.getLogger('sync_from_bookcatalogue')
LOGGER.setLevel(LOGLEVEL)

NOTE_SUFFIX = ' [BkCat]'


class Command(BaseCommand):
    help = 'Sync with export.csv created by Book Catalogue'

    def __init__(self, stdout=None, stderr=None, no_color=False):
        self._conflicts_books = []
        self.differs = {}
        super().__init__(stdout, stderr, no_color)
        
    def add_arguments(self, parser):
        parser.add_argument('--csv', default="export.csv") 

    def normalize_title(self, title):
        title = title.replace('\u00ac', '')
        # &#172;, NOT SIGN / angled dash - used to delimit optional title parts, e.g. ¬Der¬ Besucher
        return title

    def safe_get_date_iso(self, value):
        """ get string formatted date in ISO format in resilient way """
        if not value:
            return None
        date_value = None
        if len(value) < 10: # partial date
            value = value[:4] +'-01-01' # year only
        try:
            if len(value) > 10: # date with time? strip off latter
                value = value[:10]
            date_value = datetime.strptime(value, '%Y-%m-%d')
        except ValueError as err:
            LOGGER.error("failed to determine date value - %s", err)
            return None
        date_value = timezone.make_aware(date_value)
        return date_value.date()

    def safe_get_datetime_iso(self, value):
        """ get string formatted date and time in ISO format in resilient way """
        if not value:
            return None
        date_value = None
        if ' ' in value:
            value = value.replace(' ', 'T')
        value = value + 'XXXX-XX-XXT00:00:00.000'[len(value):]  # fillup missing time parts
        try:
            date_value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError as err:
            LOGGER.error("failed to determine date value - %s", err)
            return None
        date_value = timezone.make_aware(date_value)
        return date_value

    def add_book_authors(self, book_obj, author_names):
        now = timezone.now()
        added = []
        for author_info in author_names:
            author_name = self.transform_name_db(author_info)
            found = authors.objects.filter(name=author_name)
            if found:
                author_obj = found[0]
            else:
                author_parts = author_name.rsplit(' ', 1)
                author_obj = authors()
                author_obj.name = author_name
                author_obj.lowerCaseName = author_name.lower()
                author_obj.familyName = author_parts[0]
                author_obj.updated = now
                author_obj.save()
            book_obj.authors.add(author_obj)
            added.append(author_obj)
        return added
    
    def create_book_comment(self, book_obj, title, comment):
        """ create comment object for given book 
        """
        now = timezone.now()
        comment_obj = comments()
        comment_obj.book = book_obj
        comment_obj.bookTitle = title
        comment_obj.dateCreatedInt = int(now.timestamp() *1000)
        comment_obj.dateCreated = now
        comment_obj.text = comment
        comment_obj.save()
        return comment_obj
    
    def set_book_state(self, book_obj, have_read):
        states_obj = states(pk=book_obj.id)
        states_obj.book = book_obj
        if have_read == '1':
            states_obj.haveRead = True
            states_obj.readingNow = False
            states_obj.toRead = False
            states_obj.toBuy = False
        else:
            states_obj.readingNow = True
            states_obj.toRead = False
            states_obj.toBuy = False            
        states_obj.save()
        return states_obj

    def handle_new(self, row):
        """ handle case book from bookcatalog does not exist in mybookdb """
        # check if book with (book_title) in mybookdb - e.g. if added in parallel
        book_title = row['title']        
        LOGGER.info(f"new book: {row['title']!r} {row['book_uuid']}")
        book_title = self.normalize_title(row['title'])
        if book_title != row['title']:
            LOGGER.debug(f"book title normalized to {book_title!r}")
        book_info = f"{book_title!r}"
        now = timezone.now()

        # create books object
        with transaction.atomic():
            book_obj = books()            
            book_obj.title = book_title
            assert Isbn13(row['isbn']).validate(), f"book isbn is invalid: {row['isbn']} {book_info}"
            book_obj.isbn13 = row['isbn']
            book_obj.new_description = row['description'] or None  # normalize?
            book_obj.orig_description = row['description'] or ''
            book_obj.publisher =row['publisher'] or None
            book_obj.publicationDate = self.safe_get_date_iso(row['date_published'])
            book_obj.created = self.safe_get_date_iso(row['date_added']) or now
            book_obj.updated = now
            if row['read_start']:
                book_obj.read_start = self.safe_get_date_iso(row['read_start'])
            if row['read_end']:
                book_obj.read_end = self.safe_get_date_iso(row['read_end'])
            
            if row['rating'] and Decimal(row['rating']) != Decimal(0):
                book_obj.userRating = Decimal(row['rating'])

            # ignored: 'bookshelf_id', 'bookshelf', 'location', 'anthology', 'signed', 'loaned_to', 'anthology_titles'
            assert row['anthology'] == '0'  # what else, from bookcatalogue sync with goodreads ...?

            book_series = self.get_book_series(row["series_details"], book_info)
            if len(book_series) > 1:
                LOGGER.info(f'pick only first book series for {book_info}: {book_series}')
                series_name = book_series[0]
            elif len(book_series) == 1:
                series_name = book_series[0]                
            else:
                series_name = ''
            book_obj.book_serie = series_name

            """
            FUTURE consider updating book_obj (and related) for the following properties:
            row['pages']  # vs length from onleihe (pages vs minutes)
            row['format']  # book, ebook or eaudio?
            row['genre']
            row['goodreads_book_id']
            row['last_goodreads_sync_date']
            row['last_update_date']
            """

            book_obj.new_description = self.denormalize_description(row['description'])
            
            book_obj.language = row['language']
            book_obj.bookCatalogueId = uuid.UUID(row['book_uuid'])
            book_obj.synced = datetime.now(timezone.utc)
            book_obj.save()
            book_info = f"{book_title!r} id={book_obj.id}"

            # comment book creation in BookCatalogue app
            date_added = self.safe_get_datetime_iso(row['date_added'])
            comment = "added %s from bookcatalogue (created=%s)" % (now.date().isoformat(), date_added.date().isoformat())
            self.create_book_comment(book_obj, row['title'], comment)

            self.set_book_state(book_obj, row['read'])

            if row['notes']:
                comment = row['notes'] + NOTE_SUFFIX
                self.create_book_comment(book_obj, book_title, comment)
                        
            # add authors from author_details
            authors = row['author_details'].split('|')
            self.add_book_authors(book_obj, authors)
                
        self.new_books.append(book_info)
        return

    def get_book_series(self, book_series, book_info):
        if not book_series:
            return []
        book_series = [sn.strip() for sn in book_series.split('|')]
        series = []
        for series_name in book_series:
            series_name = series_name.strip()
            if not series_name:
                continue
            # drop pseudo series names found in sync data
            if series_name not in ('German Edition', 'mit Bonusgeschichten', 'Ab 10 J.'):
                series.append(series_name)
        return series
    
    def check_differs(self, field_name, bk_value, db_value, book_info):
        if db_value != bk_value:
            if book_info is not None:
                LOGGER.warning(f"""book {field_name} differs for {book_info}:
                  bk_{field_name}={bk_value!r}
                  db_{field_name}={db_value!r}
                  """)
            return True
        else:
            return False

    def lookup_isbn(self, isbn):
        metadata = {}
        for service in ('goob','openl','wiki'):
            # 'goob' for google books, 'wiki' for wikipedia, 'openl' for openlibrary
            try:          
                metadata = isbnlib.meta(isbn, service=service)
                metadata['ISBN'] = isbn
                if metadata:
                    break
            except DataNotFoundAtServiceError:
                LOGGER.debug("lookup isbn %r service=%r - not found", isbn, service)
            except isbnlib._exceptions.NotValidISBNError:
                LOGGER.warning("not a valid ISBN number: %r", isbn)
                metadata['Title'] = "ISBN not valid: %s" % isbn
                break
            except Exception as err:
                # socket.timeout if no access to internet or backend service
                # NotValidISBNError
                LOGGER.error("failed to lookup book metadata for isbn=%s service=%r: %r", isbn, service, err)
            metadata = {}
        return metadata
        
    def check_isbn_differs(self, bk_value, db_obj, book_info):
        db_value = db_obj.isbn13
        if db_value != bk_value:
            # lookup ISBN using isbnlib, check titles / author
            meta_db = self.lookup_isbn(db_obj.isbn13)
            meta_bk = self.lookup_isbn(bk_value)
            if book_info is not None:
                LOGGER.warning(f"""book isbn differs for {book_info}:
                  bk_isbn={bk_value!r} - {meta_bk.get('Title', None)!r} {', '.join(meta_bk.get('Authos', []))} {meta_bk.get('Publisher','--')}
                  db_isbn={db_value!r} - {meta_db.get('Title', None)!r} {', '.join(meta_db.get('Authos', []))} {meta_db.get('Publisher','--')}
                  """)
            return True
        return False
            
    def check_title_differs(self, bk_value, db_obj, book_info):
        titles = set()
        db_title = db_obj.title
        titles.add(db_obj.book_title)
        titles.add(db_title)
        for title in list(titles): 
           for part in ('A', 'The'):
                if title.endswith(', '+part):
                    # e.g. 'Princess of Mars, A' => 'A Princess of Mars'
                    new_title = part + ' ' + title[:-len(part)-2]
                    titles.add(new_title)
                elif title.endswith(part):
                    TODOverify = title
        
        if bk_value not in titles:
            if book_info is not None:
                LOGGER.warning(f"""book title differs for {book_info}:
                  bk_title={bk_value!r}
                  db_title={db_title!r}
                  """)
            return True
        else:
            return False

    def normalize_description(self, description):
        """ normalize book description so it can be compared what is written to export.csv by bookcatalogue """
        if not description:
            return ''
        description = description.replace('\r\n', '\n')  # linux style line-ends
        description = description.replace('\n', '\\n')  # single line, so escape newlines
        description = description.replace('\t', '\\t')  # single line, so escape newlines
        description = description.replace(u'\u2013', '-')  # endash x8211
        #description = description.replace('"', '""')  #TODO drop this
        return description
    
    def denormalize_description(self, description):
        if not description:
            return None
        description = description.replace('\\n', '\n')
        description = description.replace('\\t', '\t')
        return description

    def transform_name_db(self, parts):
        """ transform name from (name), (forname) to (forname) (name) format"""
        if isinstance(parts, str):
            parts = [a.strip() for a in parts.split(',') if a.strip()]
        if len(parts) == 2:
            return "%s %s" % (parts[1], parts[0])
        else:
            # e.g. 'Klabund', 'Pociao'
            assert len(parts) == 1, "unrecogized author name / format"
            return parts[0]
        
    def handle_existing(self, row, found):
        book_title = row['title']
        LOGGER.debug(f"syncing book {book_title!r} {row['book_uuid']}...")
        assert len(found) == 1, "result not unique for %r" % book_title
        book_obj = found[0]
        book_info = f"{book_title!r} id={book_obj.id}"
        
        updated = []
        diff = self.differs.get(book_info, set())
        if book_obj.states.obsolete or book_obj.states.private:
            LOGGER.warning(f"book should not be in bookcatalogue, check state: {book_info}")
            self._conflicts_books.append(f"{book_info} -- state {book_obj.states}")
            return
        
        if self.check_title_differs(book_title, book_obj, book_info):
            if not book_obj.unified_title:
                book_obj.unified_title = book_obj.title
            book_obj.title = book_title    
            updated.append('title')

        if self.check_isbn_differs(row['isbn'], book_obj, book_info):
            # requires manual correction in BookCatalogue (or myBookDb)
            diff.add('isbn')
        
        new_authors = set([a.name for a in book_obj.authors.all()])
        for author in row['author_details'].split('|'):
            author_name = self.transform_name_db(author) 
            if author_name in new_authors:
                new_authors.discard(author_name)  # already set
            elif author == "Author, Unknown":
                # get rid of / discard
                LOGGER.warning(f"unknown author assigned to {book_obj}")
            else:
                LOGGER.info(f"new author {author_name!r} for book {book_info}")
                diff.add('authors/missing')
        if new_authors:
            for author_name in new_authors:
                found = authors.objects.filter(name=self.transform_name_db(author_name))
                if not found:
                    LOGGER.warning(f"unknown author in mybookdb: {author_name!r}")
                    diff.add('authors/unknown')
                else:
                    LOGGER.warning(f"author not assigned: {author_name} for {book_info}")
                    diff.add('authors/extra')

        book_series = self.get_book_series(row["series_details"], book_info)
        if book_series:
            series_name = ''
            if book_obj.book_serie:  # lookup assigned series name
                for name in book_series:
                    if not self.check_differs('series_details', name, book_obj.book_serie or '', None):
                        series_name = name  # known
                        break
                    LOGGER.info(f"series name not matched: {name!r} for {book_info}")
            if not series_name:
                if len(book_series) > 1:
                    LOGGER.info(f'pick only first book series for {book_info}: {book_series}')
                series_name = book_series[0]
                if self.check_differs('series_details', series_name, book_obj.book_serie or '', book_info):
                    if not book_obj.book_serie:
                        LOGGER.info(f"set book_serie to {series_name!r} for book {book_info}")
                        book_obj.book_serie = series_name
                        updated.append('series_details')
                    else:
                        diff.add('series_details')
        
        show_diff = (book_obj.states.haveRead == '1') and book_info or None
        if self.check_differs('read', row["read"], book_obj.states.haveRead and '1' or '0', show_diff):
            if row['read'] == '1':
                # marked read in bookcatalogue, so update in mybookdb
                LOGGER.info(f"auto-update book {book_info}, state read={row['read']} => .haveRead")
                book_obj.states.haveRead = True
                book_obj.states.readingNow = False
                book_obj.states.toRead = False
                book_obj.toBuy = False
                book_obj.states.save()
                updated.append('read')
            else:
                # do not attempt to fix that, report only
                LOGGER.warning(f"mismatch book state read={row['read']} != .haveRead={book_obj.states.haveRead!r}")
                diff.add('read')

        show_diff = (book_obj.language != None) and book_info or None
        if self.check_differs('language', row['language'], book_obj.language, show_diff):
            if book_obj.language is None:
                book_obj.language = row['language']
                updated.append('language')                
            else:
                diff.add('language')
        
        if self.check_differs('publisher', row['publisher'], book_obj.publisher, None):
            LOGGER.info("auto-update publisher for %s: %r -> %r", book_info, book_obj.publisher, row['publisher'])
            book_obj.publisher = row['publisher']  # always update if not set or different
            updated.append('publisher') 
            
        date_published = self.safe_get_date_iso(row['date_published'])
        show_diff = (book_obj.publicationDate != None) and book_info or None
        if date_published and self.check_differs('date_published', date_published, book_obj.publicationDate, show_diff):
            if book_obj.publicationDate:
                # happens if book description for other format / different publisher
                # use date from BookCatalogue to reduce logging for future syncs
                LOGGER.info("autp-update date_published for %s: %r -> %r", book_info, book_obj.publicationDate, date_published)
                book_obj.publicationDate = date_published
                updated.append('date_published')
            else:
                book_obj.publicationDate = date_published  # always update from Bk
                updated.append('date_published')                

        userRating = book_obj.userRating or Decimal('0.0')
        userRatingBk = Decimal(row['rating'] or '0.0')
        show_diff = (userRating != Decimal('0.0')) and book_info or None
        if self.check_differs('rating', userRatingBk, userRating, show_diff):
            if userRating == Decimal(0):  # not yet rated, take what Bk proposes
                 book_obj.userRating = userRatingBk
                 updated.append('userRating')
            else:
                diff.add('rating')
            
        notes = row['notes']
        if notes:
            # do not sync notes - unless created in BookCatalogue app directly
            book_comments = [cmt.text for cmt in comments.objects.filter(book=book_obj)]
            if not notes in book_comments and not notes + NOTE_SUFFIX in book_comments:
                now = timezone.now()
                comment_obj = comments()
                comment_obj.bookTitle = book_obj.book_title
                comment_obj.dateCreatedInt = int(now.timestamp() *1000)
                comment_obj.dateCreated = now
                comment_obj.text = notes + NOTE_SUFFIX
                comment_obj.book = book_obj
                LOGGER.info(f"update {book_info} add note from Bk: {notes!r}")
                comment_obj.save()
                updated.append('notes') 

        bookshelf = row['bookshelf']  # 'bookshelf_id', 'bookshelf'
        bookshelves = set([shelf.strip() for shelf in bookshelf.split(',') if shelf.strip()])
        bookshelves.discard('Default')
        if bookshelves:
            LOGGER.debug(f"book on bookshelf {bookshelf!r} id={row['bookshelf_id']} - {book_info}")
            pass
            
        if row['genre']:
            LOGGER.debug(f"book genre {row['genre']!r} - {book_info}")

        book_description = self.normalize_description(book_obj.description)
        orig_description = book_obj.orig_description
        bk_description = self.normalize_description(row['description'])
        if not bk_description:
            LOGGER.warning(f"no description for {book_info} in bookcatalogue")
            FUTURE = 1 # FUTURE: how to handle this?
        elif bk_description != book_description:
            diff_pos = [pos for pos, li in enumerate(difflib.ndiff(bk_description, book_description)) if li[0] != ' ']
            # SequenceMatcher .find_longest_match, .ratio
            pos_start = diff_pos[0]
            if pos_start != 0:
                LOGGER.info('differences in pos %s ...', diff_pos[:3])

            if book_obj.orig_description != book_obj.description:                
                LOGGER.info(f"save former description in orig_description for {book_info}")
                book_obj.orig_description = book_obj.description
                updated.append('orig_description')
                
            LOGGER.warning(f"difference in description for {book_info}\n  bk: %s\n  db: %s",
                           self.pp_description(row['description']),
                           self.pp_description(book_obj.description)
                           )
            book_obj.description = row['description']
            updated.append('description')
            diff.add('description')
            
        assert row['anthology'] == '0'  # anthology not supported by sync
        
        read_start = self.safe_get_date_iso(row['read_start'])
        show_diff = (book_obj.read_start is not None) and book_info or None
        if read_start and self.check_differs('read_start', read_start, book_obj.read_start, show_diff):
            if book_obj.read_start:
                if read_start < book_obj.read_start:
                    # update if date in mybookdb before 
                    updated.append('read_start')
                    book_obj.read_start = read_start
                else:
                    diff.add('read_start')
            else:
                book_obj.read_start = read_start  # update if not yet set
                updated.append('read_start')
        
        read_end = self.safe_get_date_iso(row['read_end'])
        show_diff = (book_obj.read_end is not None) and book_info or None
        if read_end and self.check_differs('read_end', read_end, book_obj.read_end, show_diff):
            if book_obj.read_end:
                if read_end < book_obj.read_end:
                    # update if date in mybookdb before 
                    book_obj.read_end = read_end
                    updated.append('read_end')
                else:
                    diff.add('read_end')
            else:
                book_obj.read_end = read_end  # update if not yet set
                updated.append('read_end')
        
        # 
        # fields maybe of interest (in future):
        # 'pages', 'format'
        # 'goodreads_book_id',
        #
        # fields not of interest / ignored (for updates):
        # 'signed', 'loaned_to', 'anthology_titles', 'date_added'
        # 'location', 'list_price', 'anthology', 
        
        if updated:
            book_obj.synced = datetime.now(timezone.utc)
            book_obj.save()
            self.updated_books[book_info] = updated
        if diff:
            self.differs[book_info] = diff
        return
        
    def setup_logging(self):
        """ setup file logging """
        # ATTN to be called only once
        now = datetime.now().isoformat('T').replace(':', '')
        log_path = Path('log', 'sync_from_bookcatalogue.%s.log' % now)
        log_handler = logging.FileHandler(log_path.as_posix(), encoding='utf-8-sig', delay=True)
        log_fmt = logging.Formatter(fmt=LOG_FORMAT_EX, datefmt=LOG_DATE_FORMAT)
        log_handler.setFormatter(log_fmt)
        if LOGLEVEL in ('DEBUG', 'INFO'):
            log_handler.setLevel(LOGLEVEL)
        else:
            log_handler.setLevel('INFO')            
        LOGGER.addHandler(log_handler)
        
    def pp_description(self, value, start=0, maxlength=96):
        if start < 0:
            start = 0
        ppv = value.replace('\n', '| ')
        if start > 0:
            ppv = '..' +ppv[start:]            
        if len(ppv) > maxlength:
            ppv = '%r..' % ppv[:maxlength]
        else:
            ppv = '%r' % ppv
        return ppv
    
    def handle_book(self, row):
        """ handle book info from bookcatalogue """
        book_title = row['title']
        book_uuid = row['book_uuid']
        found = books.objects.filter(bookCatalogueId=book_uuid)
        if not found:
            # check if book exists with same name on both sides
            found = books.objects.filter(title=book_title)
            if not found:
                found = books.objects.filter(unified_title=book_title)
            if found:
                books_found = [ b for b in found if not b.states.obsolete ]
                if len(books_found) != 1:
                    ids_found = ','.join([ str(b.id) for b in found ])
                    LOGGER.error(f"multiple books for {book_title!r} - {ids_found}")
                    # dont know how to handle this # FUTURE
                    return
                
                book_obj = books_found[0]
                # assume happend because book added both to BookCatalogue and MyBookDB - so fix to match
                book_info = f"{book_title!r} id={book_obj.id}"
                if book_obj.bookCatalogueId is not None:
                    LOGGER.warning(f'found book with title {book_title!r} but different uuid - autocorrected')
                    self.differs[book_info] = set(('uuid',))
                    self.updated_books.add(book_info)                    
                    #self._conflicts_books.append(f"{book_obj.book_title!r} id={book_obj.id} -- not matching book_uuid={uuid.UUID(book_uuid)}")
                else:
                    LOGGER.info(f"linked book from BkCatalog with {book_info} - assigning uuid {book_uuid}")
                book_obj.bookCatalogueId = book_uuid
                book_obj.save()
                found = books_found
            
        if not found:
            self.handle_new(row)
            
        else:
            self.handle_existing(row, found)
        
    def handle(self, *args, **options):
        csv_path = Path(options['csv'])
        modified = datetime.fromtimestamp(csv_path.stat().st_mtime).date().isoformat()
        
        # send log msgs to logfile
        self.setup_logging()
        
        LOGGER.info(f"sync with bookcatalog export {csv_path!r} modified {modified}")
        assert csv_path.is_file(), f"missing csv path {csv_path!r}"
        
        rows = updated = new = differs = 0
        self.new_books = []
        self.updated_books = dict()
        self.differing = {}
        with csv_path.open('r', encoding='utf-8') as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                rows += 1
                self.handle_book(row)
                
        LOGGER.info(f"processed totally {rows} rows from {csv_path.name}")
        if self.new_books:
            LOGGER.info(f"added books from {csv_path.name} (%s):\n  + %s\n" % 
                        (len(self.new_books), "\n  + ".join(self.new_books)))   
        if self.updated_books:
            update_info = []
            for book_info, updated in self.updated_books:
                update_info.append("%s - %s" % (book_info, updated))
            LOGGER.info(f"updated books from {csv_path.name} (%s):\n  + %s\n" % 
                        (len(self.updated_books), "\n  + ".join(update_info)))        
        if self.differs:
            diff_info = []
            for book_title in self.differs:
                diff = self.differs[book_title]
                diff_info.append(f"{book_title} differs in {diff}")
            LOGGER.warning(f"found {len(self.differs)} books with differences:\n   %s\n.", '\n   '.join(diff_info))
        
        if self._conflicts_books:
            LOGGER.warning("conflicting books in bookcatalogue (%s):\n- %s\n.", 
                           len(self._conflicts_books), 
                           '\n- '.join(self._conflicts_books))
        return
        
        


