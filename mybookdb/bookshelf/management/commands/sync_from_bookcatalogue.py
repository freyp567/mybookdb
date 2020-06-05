"""
sync mybookdb with information from Book Catalogue export.csv

"""

import os
import sys
from pathlib import Path
import csv

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookshelf.models import books, authors #, comments, grBooks, googleBooks

import logging 
LOG_FORMAT = "%(levelname)-8s %(message)s"
LOG_DATE_FORMAT = "%m-%dT%H:%M:%S"
LOGLEVEL = os.environ.get('LOGLEVEL') or logging.INFO
logging.basicConfig(stream=sys.stdout, level=LOGLEVEL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
#logging.basicConfig()
for logname in ('', 'django.db.backends'):
    logging.getLogger(logname).setLevel('INFO')
LOGGER = logging.getLogger('sync_from_bookcatalogue')
LOGGER.setLevel(LOGLEVEL)


class Command(BaseCommand):
    help = 'Sync with export.csv created by Book Catalogue'

    def __init__(self, stdout=None, stderr=None, no_color=False):
        self._conflicts_books = []
        self.differs = {}
        super().__init__(stdout, stderr, no_color)
        
    def add_arguments(self, parser):
        parser.add_argument('--csv', default="export.csv") 

    def handle_newbook(self, row):
        # check if book with (book_title) in mybookdb - e.g. if added in parallel
        book_title = row['title']
        found = books.objects.filter(title=book_title)
        assert not found, f'found book with title {book_title!r}'  #TODO requires ahndling - future
        
        LOGGER.info(f"new book: {row['title']!r} {row['book_uuid']}")            
        
        #TODO create books object
        #book_obj = books() ...
        return True

    def get_book_series(self, book_series, book_info):
        if not book_series:
            return []
        book_series = [sn.strip() for sn in book_series.split('|')]
        series = []
        for series_name in book_series:
            series_name = series_name.strip()
            if not series_name:
                 continue
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

    def transform_name_db(self, parts):
        """ transform name from (name), (forname) to (forname) (name) format"""
        if isinstance(parts, str):
            parts = [a.strip() for a in parts.split(',')]
        if len(parts) == 2:
            return "%s %s" % (parts[1], parts[0])
        else:
            assert len(parts) == 1
            return parts[0]
        
    def handle_existing(self, row, found):
        book_title = row['title']
        LOGGER.debug(f"syncing book {book_title!r} {row['book_uuid']}...")
        assert len(found) == 1, "result not unique"
        book_obj = found[0]
        book_info = f"{book_title!r} id={book_obj.id}"
        
        updated = []
        diff = set()
        if book_obj.states.obsolete or book_obj.states.private:
            LOGGER.warning(f"book should not be in bookcatalogue, check state: {book_info}")
            self._conflicts_books.append(f"{book_info} -- state {book_obj.states}")
            return diff, updated

        if self.check_differs('title', book_title, book_obj.book_title, book_info):
            new_title = None
            for part in ('A', 'The'):
                if book_title.endswith(', '+part) and book_obj.book_title.startswith(part):
                    new_title = book_title
                    break
            if new_title:
                book_obj.unified_title = new_title
                updated.append('title')
            else:
                diff.add('title')
            
        if self.check_differs('isbn', row['isbn'], book_obj.isbn13, book_info):
            diff.add('title')
        
        all_authors = set([a.name for a in book_obj.authors.all()])
        for author in row['author_details'].split('|'):
            author_name = self.transform_name_db(author) 
            if author_name in all_authors:
                all_authors.discard(author_name)
            #elif author.replace(',', '') in all_authors:
            #    author = author.replace(',', '')
            #    LOGGER.info(f"mangled author names: {author!r} vs {author_name!r} for book {book_info}")
            #    all_authors.discard(author)
            #    diff.add('authors/mangled')
            else:
                LOGGER.info(f"new author {author_name!r} for book {book_info}")
                diff.add('authors/missing')
        if all_authors:
            for author_name in all_authors:
                found = authors.objects.filter(name=self.transform_name_db(author_name))
                if not found:
                    LOGGER.warning(f"unknown author in mybookdb: {author_name!r}")
                    diff.add('authors/unknown')
                else:
                    LOGGER.warning(f"author not assigned: {author_name} for {book_info}")
                    diff.add('authors/extra')

        book_series = self.get_book_series(row["series_details"], book_info)
        if len(book_series) > 1:
            LOGGER.info(f'pick only first book series for {book_info}: {book_series}')
            series_name = book_series[0]
        else:
            series_name = book_series and book_series[0] or ''
        if self.check_differs('series_details', series_name, book_obj.book_serie or '', book_info):
            if not book_obj.book_serie:
                book_obj.book_serie = book_series
                updated.append('series_details')
            else:
                diff.add('series_details')
        
        if self.check_differs('read', row["read"], book_obj.states.haveRead and '1', book_info):
            # do not attempt to fix that, report only
            diff.add('read')
            
        # 'publisher', 'date_published', 'rating', 
        #  'notes', 
        # 'description', 'genre', 'language'
        # 
        # fields maybe of interest (in future):
        # 'pages', 'format'
        # 'goodreads_book_id',
        # 'read_start', 'read_end'
        # 'bookshelf_id', 'bookshelf', 
        #
        # fields not of interest:
        # 'signed', 'loaned_to', 'anthology_titles', 'date_added'
        # 'location', 'list_price', 'anthology', 
        #
        if updated:
            book_obj.save()
        return diff, updated        
        
    def handle(self, *args, **options):
        csv_path = Path(options['csv'])
        LOGGER.info(f"sync with bookcatalog export {csv_path!r}")
        assert csv_path.is_file(), f"missing csv path {csv_path!r}"
        
        rows = updated = new = differs = 0
        self.differs = {}
        with csv_path.open('r', encoding='utf-8') as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                rows += 1
                book_title = row['title']
                book_uuid = row['book_uuid']
                found = books.objects.filter(bookCatalogueId=book_uuid)
                if not found:
                    if self.handle_newbook(row):
                        new += 1                
                    
                else:
                    diff, updates = self.handle_existing(row, found)
                    if updates:
                        updated += 1
                    if diff:
                        self.differs[book_title] = diff
                        differs += 1
                
        if new:
            LOGGER.info(f"added {new} books from {csv_path.name}")            
        if self.differs:
            diff_info = []
            for book_title in self.differs:
                diff = self.differs[book_title]
                diff_info.append(f"{book_title} differs in {diff}")
            LOGGER.info(f"found {len(self.differs)} books with differences:\n%s\n.", '   '.join(diff_info))
        LOGGER.info(f"updated {updated} rows of totally {rows} entries in {csv_path.name}")
        
        if self._conflicts_books:
            LOGGER.warning("conflicting books in bookcatalogue (%s):\n- %s\n.", 
                           len(self._conflicts_books), 
                           '- '.join(self._conflicts_books))
        return
        
        


