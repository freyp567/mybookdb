"""
functionality to export book related information
"""

# -*- coding: utf-8 -*-
"""
views on bookshelf (books, authors, ...)
"""
import os
import logging

from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from bookshelf.forms import BookExportForm

LOGGER = logging.getLogger(name='mybookdb.bookshelf.export')


class BookExportView(FormView):
    template_name = 'exportbooks.html'
    form_class = BookExportForm
    success_url = reverse_lazy('bookshelf:book-export-run')
    
    def form_valid(self, form):
        LOGGER.debug("start exporting books ...")
        return super().form_valid(form)


def export_books(request):
    LOGGER.debug("exporting books ...")
    return  #xxx TODO show status of export (complete, ...)
