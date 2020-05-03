"""
functionality to export book related information
"""

# -*- coding: utf-8 -*-
"""
views on bookshelf (books, authors, ...)
"""
import logging
import shutil
from pathlib import Path
import zipfile
from datetime import datetime

from django.urls import reverse_lazy
from django.conf import settings
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


def export_books(request):
     
    export_path = Path(request.POST['export_path']).absolute()
    LOGGER.debug(f"exporting books to {export_path} ...")

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
            LOGGER.warning("ignore book without state: bookid=%s %s", book_obj.id, book_obj)

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
    # content_type="application/zip"
    # TODO FileResponse with redirect?
