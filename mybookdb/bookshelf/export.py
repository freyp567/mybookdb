# -*- coding: utf-8 -*-
"""
functionality to export book related information
views on bookshelf (books, authors, ...)
"""
import logging
import shutil
from pathlib import Path
import zipfile
import csv
from datetime import datetime
import uuid

from django.urls import reverse_lazy
from django.http import FileResponse
from django.views.generic.edit import FormView

from django.core import serializers

from bookshelf.forms import BookExportForm
from bookshelf.models import books, authors
from timeline.models import timelineevent, DatePrecision

LOGGER = logging.getLogger(name='mybookdb.bookshelf.export')

TIME_EPOQUES= [
    # https://de.wikipedia.org/wiki/Geschichte_Europas
    (2000, "2000 .. Gegenwart"),
    (1960, "1960 .. 2000"),
    (1945, "1945 .. 1960 Nachkriegszeit"),
    (1939, "1939 .. 1945 2.WK"),
    (1918, "1918 .. 1939 Zwischenkriegszeit"),
    (1914, "1914 .. 1918 1.WK"),
    (1884, "1884 .. 1914 Belle Epoque"),  # https://de.wikipedia.org/wiki/Belle_%C3%89poque
    (1800, "19.Jh",),
    (1700, "18.Jh",),
    (1600, "17.Jh",),
    (1500, "16.Jh",),
    (1400, "15.Jh",),
    (1300, "14.Jh",),
    (1200, "13.Jh",),
    (1100, "12.Jh",),
    (1000, "11.Jh",),
    ( 900, "10.Jh",),
    ( 500, "Frühmittelalter",),  # https://de.wikipedia.org/wiki/Fr%C3%BChmittelalter
    ( 284, "Spätantike",),  # https://de.wikipedia.org/wiki/Sp%C3%A4tantike
    (-800, "Antike",),  # Antike 800 vChr bis 600 n Chr
    # https://de.wikipedia.org/wiki/Altertum
    (-4000, "Altertum",),  # Altertum 4000 / 3500 vChr .. 
    # https://de.wikipedia.org/wiki/Fr%C3%BChgeschichte
    # https://de.wikipedia.org/wiki/Geschichte_Europas
    # Frühgeschichte (Urgeschichte, Mittelsteinzeit, Jungsteinzeit, Bronzezeit, Eisenzeit, Hochkulturen)]
    (-9999, "Frühgeschichte",),
]


class BookExportView(FormView):
    template_name = 'bookshelf/exportbooks.html'
    form_class = BookExportForm
    success_url = reverse_lazy('bookshelf:book-export-run')
    
    def form_valid(self, form):
        LOGGER.debug("start exporting books ...")
        return super().form_valid(form)


def zip_dir(filename: str, to_zip: Path):
    """ generate zipfile from directory tree """
    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for directory in to_zip.glob('**'):
            for file in directory.iterdir():
                if not file.is_file():
                    continue
                # Strip first component, so we don't create unneeded subdirectory
                # zip_path = Path(*file.parts[1:])
                zip_path = file.relative_to(to_zip)
                zipf.write(file.as_posix(), zip_path.as_posix())
    return


def escape_text_csv(value):
    if not value:
        return ''
    value = value.replace('\r\n', '\n')
    value = value.replace('\n', '\\n')
    value = value.replace('\t', '\\t')
    #value = value.replace('"', '""')
    #value = value.encode('latin-1', 'xmlcharrefreplace').unicode('latin-1')  # normalize charset
    return value


def format_author_names(authors):
    names = []
    for author in authors:
        name = author.name.split(' ')
        if len(name) > 1:
            nl = len(name) -1
            names.append('%s, %s' % (name[nl], ' '.join(name[:nl])))
        #else:
        #    names.append(name[0])
    return '|'.join(names)

def get_timeline_info(book_obj):
    epoque = notes = ''
    start_event = None
    event_last = None
    is_bc = False
    start_event = None
    for event in timelineevent.objects.filter(book=book_obj).order_by('date'):
        if event.is_bc:
            is_bc = True
        if not start_event:
            start_event = event
            event_last = event.date
        if event.date > event_last:
            event_last = event.date
            
    if start_event is None:
        epoque = 'Unknown'
        notes = '(no timeline event)'
    elif start_event.precision in (
        DatePrecision.NOTDETERMINED,  # used for dates added before introduction of DatePrecision
        DatePrecision.EXACT_YEAR,
        DatePrecision.EXACT_DATE,
        DatePrecision.APPROX_YEAR,
        DatePrecision.APPROX_DECADE,
        DatePrecision.APPROX_CENTURY,
        DatePrecision.APPROX_GUESSED,
    ):
        if is_bc:
            year = start_event.date.date.year * -1
            notes = f"{year} BC"
        else:
            year = start_event.date.date.year
            
        epoque = 'Unknown'
        for year_start, epoque_name in TIME_EPOQUES:
            if year >= year_start:
                epoque = epoque_name
                break

        if event_last and event_last != start_event.date:
            year_to = event_last.date.year
            notes = f"{year} .. {year_to}"
        else:
            notes = f"{year}"

    else:
        # future, fantasy, unknown, ...
        if start_event.precision == DatePrecision.NEAR_FUTURE:
            epoque = 'Zukunft nahe'
        elif start_event.precision == DatePrecision.FAR_FUTURE:
            epoque = 'Zukunft ferne'
        elif start_event.precision == DatePrecision.FUTURE:
            epoque = 'Zukunft'
        elif start_event.precision == DatePrecision.UNKNOWN:
            epoque = 'Epoche unbekannt'
        else:
            epoque = 'Epoche unbekannt'
    assert not ',' in epoque
    return notes, "z " +epoque
    

def export_books_bookcatalogue(export_path):
    LOGGER.debug(f"exporting books to {export_path} BookCatalogue CSV ...")
    # see https://github.com/eleybourn/Book-Catalogue/wiki/Export-Import-Format
    csv_fields = (
        '_id',
        'author_details',
        'title',
        'isbn',
        'publisher',
        'date_published',
        'rating',
        'bookshelf_id',
        'bookshelf',
        'read',
        'series_details',
        'pages',
        'notes',
        'list_price',
        'anthology',
        'location',
        'read_start',
        'read_end',
        'format',
        'signed',
        'loaned_to',
        'anthology_titles',
        'description',
        'genre',
        'language',
        'date_added',
        'goodreads_book_id',
        'last_goodreads_sync_date',
        'last_update_date',        
        'book_uuid',
    )
    row_count = 0
    with open(export_path, mode='w', encoding='utf-8') as csv_f:
        writer = csv.DictWriter(csv_f, fieldnames=csv_fields, quoting=csv.QUOTE_ALL, lineterminator='\n', quotechar='"')
        writer.writeheader()
        for book_obj in books.objects.all():

            if hasattr(book_obj, "states"):
                if not book_obj.states.haveRead:
                    continue
                
                if book_obj.states.private or book_obj.states.obsolete: # do not export
                    continue
                
            else:
                LOGGER.warning(f"book without state: {book_obj}")
                continue
            
            row_count += 1
            book_uuid = book_obj.bookCatalogueId
            if not book_uuid:
                book_uuid = uuid.uuid4()
                book_obj.bookCatalogueId = book_uuid
                book_obj.save()
            
            created = book_obj.created and book_obj.created.isoformat() or ''
            updated = book_obj.created and book_obj.created.isoformat() or ''
            
            bookshelves = set()
            if book_obj.states.haveRead:
                bookshelves.add('have_read')
            elif book_obj.states.readingNow:
                bookshelves.add('reading')
            else:
                bookshelves.add('not_read')
            
            if book_obj.states.favorite:
                bookshelves.add('favorite')
            
            book_notes, epoque = get_timeline_info(book_obj)
            bookshelves.add(epoque)
                
            data = {}
            data['_id'] = ''  # using book_uuid instead, see below
            data['author_details'] = format_author_names(book_obj.authors.all())
            data['title'] = escape_text_csv(book_obj.book_title)
            data['isbn'] = book_obj.isbn13
            data['publisher'] = ''  # .publisher
            data['date_published'] = ''
            data['rating'] = book_obj.userRating or ''
            data['bookshelf_id'] = ''
            data['bookshelf'] = ','.join(bookshelves)
            data['read'] = book_obj.states.haveRead and '1' or '0'
            data['series_details'] = escape_text_csv(book_obj.book_serie)
            data['pages'] = ''  # length from onleihe (pages vs minutes)
            data['notes'] = book_notes
            data['list_price'] = ''
            data['anthology'] = '0'
            data['location'] = ''
            data['read_start'] = book_obj.read_start or ''
            data['read_end'] = book_obj.read_end or ''
            data['format'] = ''  # TODO book, ebook or eaudio?
            data['signed'] = '0'
            data['loaned_to'] = ''
            data['anthology_titles'] = ''
            data['description'] = escape_text_csv(book_obj.description)
            data['genre'] = ''  # TODO set this to what?
            data['language'] = book_obj.language
            data['date_added'] = ''
            data['goodreads_book_id'] = ''
            data['last_goodreads_sync_date'] = ''
            data['last_update_date'] = updated
            data['book_uuid'] = book_uuid.hex  # UUID without dashes
            
            writer.writerow(data)

    LOGGER.info("exported totally %s book entries", row_count)
    return FileResponse(open(export_path, 'rb'))  # as_attachment=True ?
    

def export_books_serialized(export_path):
    """ export book and author information using Django serialization """
    LOGGER.debug(f"exporting books to {export_path} (Django serialied) ...")

    # preparations
    dump_dir = Path("export_" +datetime.now().strftime("export_%Y%m%dT%H%M%S.%f"))
    dump_dir = dump_dir.absolute()
    dump_dir.mkdir(exist_ok=False)
    
    # generate books info
    for book_obj in books.objects.all():
        book_dir = dump_dir / 'book_{:04}'.format(book_obj.id)
        book_dir.mkdir()
        book_data = book_dir / 'book_{:04}.yml'.format(book_obj.id)
        with book_data.open("w", encoding='utf-8') as out:
            serializers.serialize("yaml", [ book_obj, ], stream=out)            

        try:
            book_state = book_obj.states
            book_data = book_dir / 'state_{:04}.yml'.format(book_obj.id)
            with book_data.open("w", encoding='utf-8') as out:
                serializers.serialize("yaml", [ book_state, ], stream=out)
        except Exception as err:
            # some rare cases raising RelatedObjectDoesNotExist
            LOGGER.warning("ignore book without state: bookid=%s % - %r", book_obj.id, book_obj, err)

        comments = book_obj.comments_set.all().order_by('-id')
        if len(comments) > 0:
            book_data = book_dir / 'comments_{:04}.yml'.format(book_obj.id)
            with book_data.open("w", encoding='utf-8') as out:
                serializers.serialize("yaml", list(comments), stream=out)

        events = timelineevent.objects.filter(book=book_obj).order_by('-pk')
        if len(events) > 0:
            book_data = book_dir / 'event_{:04}.yml'.format(book_obj.id)
            with book_data.open("w", encoding='utf-8') as out:
                serializers.serialize("yaml", events, stream=out)

    # dump authors info
    all_authors = authors.objects.all().order_by('-pk')
    author_data = dump_dir / 'authors.yml'
    with author_data.open("w", encoding='utf-8') as out:
        serializers.serialize("yaml", all_authors, stream=out)    
    
    # zip and cleanup
    zip_dir(export_path, dump_dir)
    shutil.rmtree(dump_dir.as_posix())
    
    return FileResponse(open(export_path, 'rb'))  # as_attachment=True ?
    
    
def export_books(request):
    export_type = request.POST['export_type']
    export_path = request.POST['export_path']
    if '-csv' in export_type:
        export_path += '.csv'
    else:        
        export_path += '.zip'
    export_path = Path(export_path).absolute()
    if export_type == 'serialized':
        return export_books_serialized(export_path)
    elif export_type == 'bookcatalog-csv':
        return export_books_bookcatalogue(export_path)
    else:
        raise NotImplementedError("unsupported export_type=%r" % export_type)
        
