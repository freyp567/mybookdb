# -*- coding: utf-8 -*-
"""
views on bookshelf (books, authors, ...)
"""
import os
import logging
import json
from datetime import datetime
import requests
import requests_random_user_agent
import isbnlib


from django.shortcuts import render, redirect
from django.views import generic
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, Http404
from django.utils.encoding import iri_to_uri
from django.utils import timezone

from django.urls import reverse
from django.db.models import Count, Max, Avg, Q

from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt  # csrf_protect

# from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import PermissionRequiredMixin

from django_filters.views import FilterView
from django_tables2 import RequestConfig
from django_tables2.views import SingleTableMixin

from bookshelf.models import books, authors, comments, states
from bookshelf.forms import BookCreateForm, BookUpdateForm, StateUpdateForm, BookInfoForm, \
    AuthorCreateForm, AuthorUpdateForm
from bookshelf.bookstable import BooksTable, BooksTableFilter, MinimalBooksTable
from bookshelf.authorstable import AuthorsTable, AuthorsTableFilter  # , MinimalAuthorsTable
from bookshelf import metrics
from timeline.models import timelineevent

LOGGER = logging.getLogger(name='mybookdb.bookshelf.views')

SERVICEURL_WIKI = 'https://de.wikipedia.org/api/rest_v1/data/citation/mediawiki/{isbn}'
SERVICEURL_GOOBOOKS = 'https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&maxResults=3'
SERVICEURL_LIBTHING = 'http://www.librarything.com/api/thingISBN/{isbn}'

SERVICEURL_OPENLIBRRAY = "https://openlibrary.org/api/books"


class BookISBNinfoView(generic.DetailView):
    """
    detail view for ISBN related info from openlibrary
    """
    model = books
    template_name = 'bookshelf/isbn_info.html'

    def get_metadata(self, isbn, service):
        try:          
            metadata = isbnlib.meta(isbn, service=service)
        except Exception as err:
            #DataNotFoundAtServiceError
            #socket.timeout
            LOGGER.error("failed to lookup book metadata for isbn=%s service=%s: %r", isbn, service, err)
            metadata = {}
        return metadata
        
    def get_openlibrary_info(self, isbn, context):
        requests_s = requests.Session()
        url = SERVICEURL_OPENLIBRRAY +"?bibkeys=ISBN:{isbn}&format=json"
        url = url.format(isbn=isbn)
        response = requests_s.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                LOGGER.debug("openlibrary data for isbn=%s: %r", isbn, data)
                book_data = data[f'ISBN:{isbn}']
                # 'bib_key', 'preview', 'thumbnail_url', 'preview_url', 'info_url'                
                # TODO information using 'info_url'
            else:
                LOGGER.debug("openlibrary returned no data for isbn=%s", isbn)
        else:
            LOGGER.error("failed to lookup in openlibrary, status=%s", response.status_code)
        return

    def get_mediawiki_info(self, isbn, context):
        requests_s = requests.Session()
        response = requests_s.get(SERVICEURL_WIKI.format(isbn=isbn))
        data = response.json()
        if len(data) > 0:
            context['wikiinfo'] = data[0]
            if len(data) > 1:
                context['wikiinfo']['info'] = 'multiple items from de.wikipedia.org (%s)' % len(data)
        else:
            context['wikiinfo'] = {'info': 'no info from de.wikipedia.org/mediawiki'}
        return
        
    def get_googlebooks_info(self, isbn, context):
        requests_s = requests.Session()
        response = requests_s.get(SERVICEURL_GOOBOOKS.format(isbn=isbn))
        data = response.json()
        assert data['totalItems'] <= 1, f"more than one item for {{isbn}}"
        if data and data.get('items'):
            goob_id = data['items'][0]['id']
            context['goob_url'] = 'https://books.google.de/books?id=%s' % goob_id
            volumeinfo = data['items'][0].get('volumeInfo', {})
            context['goob_title'] = '%s' % volumeinfo['title']
            if 'subtitle' in volumeinfo:
                context['goob_title'] += ' (%s)' % volumeinfo['subtitle']
            context['goob_desc'] = volumeinfo.get('description', '---')
            context['goob_vol'] = volumeinfo
            accessinfo = data['items'][0].get('accessInfo', {})
            context['reader_url'] = accessinfo.get('webReaderLink')
        else:
            LOGGER.warning("no items found in googlebooks for isbn=%s", isbn)
            context['goob_url'] = ''
            context['goob_title'] = '(not found)'
            context['goob_desc'] = '---'
            context['goob_vol'] = {}
            context['reader_url'] = ''
        return
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        isbn = self.object.isbn13  # or .isbn10 ?
        LOGGER.info(f"lookup info for ISBN {isbn}")
        assert isbn, "missing isbn (isbn13)"
        for service in ('goob', 'wiki',):
            # 'goob' for google books, 'wiki' for wikipedia, 'openl' for openlibrary
            metadata = self.get_metadata(isbn, service)
            context[service] = metadata
            metadata = isbnlib.meta(isbn, service='goob')
            
        requests_s = requests.Session()
        LOGGER.debug("using UA info for requests: %s", requests_s.headers['User-Agent'])

        # 'ISBN-13', 'Title', 'Authors', 'Publisher', 'Year', 'Language'
        # determine link to google books ... and more
        
        # update context to render page with from various services
        self.get_googlebooks_info(isbn, context)
        self.get_mediawiki_info(isbn, context)
        self.get_openlibrary_info(isbn, context)
        
        context['is_paginated'] = False
        return context
    
