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
from timeline.models import timelineevent

LOGGER = logging.getLogger(name='mybookdb.bookshelf.export')


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
    value = value.replace('"', '""')
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

def export_books_bookcatalogue(export_path):
    LOGGER.debug(f"exporting books to {export_path} BookCatalogue CSV ...")
    # see https://github.com/eleybourn/Book-Catalogue/wiki/Export-Import-Format
    csv_fields = (
        '_id',
        'author_details',
        'title',
        'isbn',
        'publisher',
        'date_pbulished',
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
            
            if not book_obj.states.haveRead:
                continue
            
            row_count += 1
            book_uuid = book_obj.bookCatalogueId
            if not book_uuid:
                book_obj.bookCatalogueId = uuid.uuid4()
                book_obj.save()
            
            book_obj.created and book_obj.created.isoformat() or ''
            
            data = {}
            data['_id'] = ''  # using book_uuid instead, see below
            data['author_details'] = format_author_names(book_obj.authors.all())
            data['title'] = escape_text_csv(book_obj.book_title)
            data['isbn'] = book_obj.isbn13
            data['publisher'] = ''  # .publisher
            data['date_pbulished'] = ''
            data['rating'] = book_obj.userRating
            data['bookshelf_id'] = ''
            data['bookshelf'] = ''
            data['read'] = book_obj.states.haveRead and '1' or '0'
            data['series_details'] = escape_text_csv(book_obj.book_serie)
            data['pages'] = ''
            data['notes'] = ''
            data['list_price'] = ''
            data['anthology'] = '0'
            data['location'] = ''
            data['read_start'] = date_read
            data['read_end'] = date_read  # set to sort by 'gelesen am'
            data['format'] = ''
            data['signed'] = '0'
            data['loaned_to'] = ''
            data['anthology_titles'] = ''
            data['description'] = escape_text_csv(book_obj.new_description)
            data['genre'] = ''
            data['language'] = 'de'  # TODO fix this
            data['date_added'] = ''
            data['goodreads_book_id'] = ''
            data['last_goodreads_sync_date'] = ''
            data['last_update_date'] = ''
            data['book_uuid'] = str(book_uuid).replace('-','')
            
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
        
