"""
sync mybookdb with information from Book Catalogue export.csv

"""

import os
import sys
from pathlib import Path
import csv
from datetime import datetime
import uuid

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
        return date_value

    def add_book_authors(self, book_obj, author_names):
        now = datetime.now(tz=timezone.utc)
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
        now = datetime.now(tz=timezone.utc)
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
        else:
            states_obj.readingNow = True
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
        now = datetime.now(tz=timezone.utc)

        # create books object
        with transaction.atomic():
            book_obj = books()            
            book_obj.title = book_title
            assert Isbn13(row['isbn']).validate(), f"book isbn is invalid: {row['isbn']} {book_info}"
            book_obj.isbn13 = row['isbn']
            book_obj.new_description = row['description'] or None
            book_obj.publisher =row['publisher'] or None
            book_obj.publicationDate = self.safe_get_date_iso(row['date_published'])
            book_obj.created = now
            book_obj.updated = now
            
            if row['rating'] not in (None, '', '0'):
                book_obj.userRating = int(row['rating'])

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
            row['read_start']  # for books added through bookcatalogue - FUTURE
            row['read_end']
            row['format']  # book, ebook or eaudio?
            row['genre']
            row['goodreads_book_id']
            row['last_goodreads_sync_date']
            row['last_update_date']
            """

            book_obj.new_description = self.denormalize_description(row['description'])
            
            book_obj.language = row['language']
            book_obj.bookCatalogueId = uuid.UUID(row['book_uuid'])
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

    def normalize_description(self, description):
        """ normalize book description so it can be compared what is written to export.csv by bookcatalogue """
        if not description:
            return ''
        description = description.replace('\r\n', '\n')  # linux style line-ends
        description = description.replace('\n', '\\n')  # single line, so escape newlines
        description = description.replace('\t', '\\t')  # single line, so escape newlines
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
            parts = [a.strip() for a in parts.split(',')]
        if len(parts) == 2:
            return "%s %s" % (parts[1], parts[0])
        else:
            # e.g. 'Klabund', 'Pociao'
            assert len(parts) == 1, "unrecogized author name / format"
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
            return

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
        
        if self.check_differs('read', row["read"], book_obj.states.haveRead and '1', book_info):
            if row['read'] == '1':
                # marked read in bookcatalogue, so update in mybookdb
                LOGGER.info(f"update book state read={row['read']} => .haveRead")
            else:
                # do not attempt to fix that, report only
                LOGGER.info(f"mismatch book state read={row['read']} != .haveRead={book_obj.state.haveRead!r}")
            diff.add('read')

        if self.check_differs('language', row['language'], book_obj.language, book_info):
            if book_obj.language is None:
                book_obj.language = row['language']
                updated.append('language')                
            else:
                diff.add('language')
        
        if self.check_differs('publisher', row['publisher'], book_obj.publisher, None):
            book_obj.publisher = row['publisher']  # always update if not set or different
            updated.append('publisher')                
            
        date_published = self.safe_get_date_iso(row['date_published'])
        if date_published and self.check_differs('date_published', date_published, book_obj.publicationDate, book_info):
            if not date_published:
                diff.add('date_published')
            else:
                book_obj.publicationDate = date_published  # always update
                updated.append('date_published')                

        userRating = book_obj.userRating and str(book_obj.userRating) or '0'
        if self.check_differs('rating', row['rating'], userRating, book_info):
            diff.add('rating')
            
        notes = row['notes']
        if notes:
            # do not sync notes - unless created in BookCatalogue app directly
            book_comments = [cmt.text for cmt in comments.objects.filter(book=book_obj)]
            if not notes in book_comments and not notes + NOTE_SUFFIX in book_comments:
                now = datetime.now()
                comment_obj = comments()
                comment_obj.bookTitle = book_obj.book_title
                comment_obj.dateCreatedInt = int(now.timestamp() *1000)
                comment_obj.dateCreated = now
                comment_obj.text = notes + NOTE_SUFFIX
                comment_obj.book = book_obj
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
        if not row['description']:
            LOGGER.debug(f"no description for {book_info} in bookcatalogue")
        elif row['description'] != book_description:                
            LOGGER.info(f"difference in description for {book_info}:\ndb={book_description!r}\nbk={row['description']!r}\n.")
            diff.add('description')
            
        assert row['anthology'] == '0'  # what else, from bookcatalogue sync with goodreads ...?
        
        read_start = self.safe_get_date_iso(row['read_start'])
        if read_start and self.check_differs('read_start', read_start, book_obj.read_start, book_info):
            if book_obj.read_start:
                diff.add('read_start')
            else:
                book_obj.read_start = read_start  # update if not yet set
                updated.append('read_start')
        
        read_end = self.safe_get_date_iso(row['read_end'])
        if read_end and self.check_differs('read_end', read_end, book_obj.read_end, book_info):
            if book_obj.read_end:
                diff.add('read_end')
            else:
                book_obj.read_end = read_start  # update if not yet set
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
            book_obj.save()
            self.updated_books.append(book_info)
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
                LOGGER.error(f'found book with title {book_title!r}')
                assert len(found) == 1, f"multiple books for {book_title!r}"
                book_obj = found[0]
                self._conflicts_books.append(f"{book_obj.book_title!r} id={book_obj.id} -- not matching book_uuid={uuid.UUID(book_uuid)}")
                # requires manual fixup - best we can do is change book title by prefixing with '[dup]'
                self.create_book_comment(book_obj, book_obj.title, f"auto-renamed by sync_from_bookcatalogue, duplicate")                
                book_obj.unified_title = f"[dup] {book_obj.book_title}"
                return
            
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
        self.updated_books = []
        self.differing = {}
        with csv_path.open('r', encoding='utf-8') as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                rows += 1
                self.handle_book(row)
                
        LOGGER.info(f"processed totally {rows} rows from {csv_path.name}")
        if self.new_books:
            LOGGER.info(f"added %s books from {csv_path.name}:\n  + %s\n" % 
                        (len(self.new_books), "\n  + ".join(self.new_books)))   
        if self.updated_books:
            LOGGER.info(f"updated %s books from {csv_path.name}:\n  + %s\n" % 
                        (len(self.updated_books), "\n  + ".join(self.new_books)))        
        if self.differs:
            diff_info = []
            for book_title in self.differs:
                diff = self.differs[book_title]
                diff_info.append(f"{book_title} differs in {diff}")
            LOGGER.warning(f"found {len(self.differs)} books with differences:\n%s\n.", '\n   '.join(diff_info))
        
        if self._conflicts_books:
            LOGGER.warning("conflicting books in bookcatalogue (%s):\n- %s\n.", 
                           len(self._conflicts_books), 
                           '\n- '.join(self._conflicts_books))
        return
        
        


