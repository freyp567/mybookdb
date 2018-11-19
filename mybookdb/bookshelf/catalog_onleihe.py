# -*- coding: latin-1 -*-
"""
lookup book from bookshelf in Onleihe website
"""

import os
import logging
import json
import requests
from pathlib import Path
import urllib
import re
from lxml import etree
from pyisbn import Isbn13

from django.shortcuts import render
from django.views import generic
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.safestring import mark_safe

from django.contrib.auth.mixins import PermissionRequiredMixin

from django import forms

from bookshelf.models import books, authors, comments, states, onleiheBooks
from bookshelf.forms import BookUpdateForm, StateUpdateForm, BookInfoForm
from bookshelf.bookstable import BooksTable, BooksTableFilter, MinimalBooksTable
from bookshelf.authorstable import AuthorsTable, AuthorsTableFilter  # , MinimalAuthorsTable

from bookshelf.onleihe_client import OnleiheClient, ONLEIHE_DETAIL_FIELDS

LOGGER = logging.getLogger(name='mybookdb.bookshelf.onleihe')


def lookup_book_isbn(book_obj):
    assert isinstance(book_obj, books)
    result = {}
    result['error'] = None
    
    # use cached onleihe data to reduce impact
    cached_name = (book_obj.isbn13 or book_obj.isbn10 or 'id_%s' % book_obj.id) +'.json'
    cached_path = Path(__file__).parent / 'static' / 'onleihe'
    cached_path = cached_path / cached_name
    cached_path.resolve()
    if cached_path.exists():
        data = json.loads(cached_path.read_text())
        return data
    
    client = OnleiheClient()
    client.connect()
    
    media_info = []
    if book_obj.isbn13:
        media_info = client.search_book(isbn=book_obj.isbn13)
        isbn13 = Isbn13(book_obj.isbn13)
        isbn10 = book_obj.isbn10 or isbn13.convert()
    if not media_info:
        isbn10 = book_obj.isbn10
        if isbn10:
            media_info = client.search_book(isbn=isbn10)
        elif not book_obj.isbn10 and book_obj.isbn13:
            isbn = Isbn13(book_obj.isbn13)
            isbn10 = isbn.convert()
            media_info = client.search_book(isbn=isbn10)
        else:
            LOGGER.warning('missing isbn for book %s' % book_obj.id)
            isbn10 = None

    if not media_info:
        # lookup by ISBN not successful, search book title (fulltext)
        media_info = client.search_book(book_title=book_obj.title)
    
    if not media_info:
        LOGGER.warning("lookup on Onleihe not successful")
        result['html'] = "not found"
        result['error'] = 'book not found in onleihe'
        return result
    
    LOGGER.info("search found %s mediaInfo items" % len(media_info))
    result['details'] = all_details = []
    for item in media_info:
        media_url = item['href']
        # lookup book details from media_url, extract description, author, ...
        details = client.get_book_details(media_url)
        all_details.append(details)
    
    # display info found 
    if len(all_details) > 1:
        # more than one book matching in Onleihe 
        LOGGER.warning("found %s books in Onleihe matching book %s '%s'" % 
                       (bookobj.id, bookobj.title))
        assert False  # TODO let user pick if more than one book for given search criterias 
        
    # if unique, pick summary for selected book and store / cache in booksdb 
    # TODO via view / interaction with user
    # keys in details: 'meta-keywords', 'img_cover', 'Titel', 'Autor', '�bersetzer', 'Jahr', 'Verlag', 
    #   'Sprache', 'ISBN', 'Format', 'Umfang', 'Dateigr��e', 'keywords', 'Exemplare', 'Verf�gbar', 
    #   'Vormerker', 'Voraussichtlich verf�gbar ab', 'Kopieren'
    cached_path.write_text(json.dumps(result))
    return result

    
class OnleiheUpdateView(PermissionRequiredMixin, generic.edit.UpdateView):
    """
    Update book link/state from local bookdb info to Onleihe.
    """
    model = books  #xxx TODO separate into own table? 
    permission_required = 'bookshelf.can_edit'
    form_class = BookUpdateForm  # TODO adapt
    
    # TODO to be continued - when Onleihe returning what we need


class OnleiheView(generic.TemplateView):
    """ book info from Onleihe web service """
    template_name = "bookshelf/lookup_onleihe.html"
    #response_class = TemplateResponse
    #content_type = "text/html"
    #http_method_names = [u'get', u'post', u'put', u'delete', u'head', u'options', u'trace']
    
    def post(self, request, pk):
        book = books.objects.get(pk=pk)
        choice = request.POST.get('choice')
        #TODO if more than one book in onleihe, need user to choose one
        if not choice:
            raise ValueError("missing choice")  # TODO better error handling
            # form error
        
        # cache onleihe book details in DB
        client = OnleiheClient()
        client.connect()
        if hasattr(book, 'onleihebooks'):
            onleihe_book = book.onleihebooks
            details = client.get_book_details(onleihe_book.onleiheId)
            assert details['isbn'] == onleihe_book.isbn
            # update book fields if changed
            changed = set()
            for key in ('book_description', ):  # TODO more attributes to sync? 
                # 'Kopieren' -> 'allow_copy'
                if getattr(onleihe_book, key) != details[key]:
                    LOGGER.warning("detected change in key=%s" % key)
                    assert details[key]  # not None !
                    setattr(onleihe_book, key, details[key])
                    change.add(key)
            if changed:
                onleihe_book.save()
                
        else:
            media_url = request.POST.get('choice')
            details = client.get_book_details(media_url)
            onleihe_book = onleiheBooks(
                book=book,
                onleiheId = media_url,
                status = 'confirmed',
                )
            CACHE_FIELDS = (
                ('bookCoverURL', 'img_cover'),
                # ('translator', ''),
                # ('title', ''),
                # ('author', ''),
                ('year', ''),
                ('isbn', ''),
                # ('metaKeywords', 'meta-keywords'),
                ('keywords', ''),
                ('publisher', ''),
                # ('language', ''),
                ('format', ''),
                ('pages', (self.get_pages, 'pages')),
                ('allow_copy', (self.is_copy_allowed, 'Kopieren')),
                ('book_description', ''),
                # ('', ''),
            )
            for tgt_name, from_name in CACHE_FIELDS:
                if not from_name:  # same name
                    value = details[tgt_name]
                elif isinstance(from_name, tuple):
                    fn = from_name[0]
                    value = fn(details[from_name[1]])
                else:
                    value = details[from_name]
                setattr(onleihe_book, tgt_name, value)
                
            onleihe_book.save()
        
        context = self.get_context_data(pk=book.id)
        return super(generic.TemplateView, self).render_to_response(context)
        
        
    def is_copy_allowed(self, value):
        return value != 'nicht erlaubt'
        
    def get_pages(self, value):
        assert value.endswith(' S.')
        value = value[:-3]
        return int(value)
        
    def get_context_data(self, **kwargs):
        context = super(OnleiheView, self).get_context_data(**kwargs)
        book = books.objects.get(pk=kwargs['pk'])
        #if self.request.POST:
        #    assert False  # book info is read-only
        #    context["errors"] = "POST unsupported, view is readonly"
        #    return

        if hasattr(book, 'onleihebooks'):
            onleiheBook = book.onleihebooks
            context['onleiheId'] = onleiheBook.onleiheId
            context['mustConfirm'] = False
        else:
            onleiheBook = None
            context['onleiheId'] = None
            context['mustConfirm'] = True

        # book info from our db
        context['bookinfo_form'] = BookInfoForm(instance=book)
        context['book_id'] = book.id
        
        # with matching info from LibraryThing
        book_info = lookup_book_isbn(book)            
        
        if book_info.get('error'):
            # pass error from lookup to form message handling
            context["messages"] = [book_info.get('error')]
        
        context['details'] = []
        context['book_url'] = None
        table_data = []
        if book_info.get('details'):
            details = book_info['details']
            context['details'] = details
        
            # transform details into JSON payload for bootstrap-table
            # where the keys are in the first rows, one column per book found
            
            img_covers = [d['img_cover'] for d in details]
            book_ids = [d['book_url'].split('/')[-1] for d in details]
            
            table_data = []
            if len(details) == 1:  # found one book
                context['onleiheId'] = book_ids[0]
            row = {
                'field_name': 'choice', 
                'field_title': 'Buchauswahl',
            }
            for pos, item in enumerate(details):
                row['book%s' % (pos+1)] = book_ids[pos]
            table_data.append(row)
                
            row = {}
            for field_name, field_title, field_title_loc in ONLEIHE_DETAIL_FIELDS:
                row = {}
                row['field_name'] = field_name
                row['field_title'] = field_title_loc or field_title
                for pos, item in enumerate(details):
                    value = item.get(field_name)
                    if field_name == 'book_url':
                        value = [value, img_covers[pos]]
                    row['book%s' % (pos+1)] = value or ''
                    
                    if onleiheBook:
                        # TODO determine where differences between details item and onleiheBook
                        pass
                table_data.append(row)
                
        else:
            context['details'] = details = []
            table_data = []
            
        context["table_data"] = table_data
        context["other_books_idx"] = list(range(2, len(details)+1))
        
        return context
    
    def get_success_url(self): 
        success_url = reverse('book-detail', args=(self.object.id,))
        return success_url
