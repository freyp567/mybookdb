"""
views on bookshelf (books, authors, ...)
"""

import os
import logging
import json
import requests
import urllib
from lxml import etree
from pyisbn import Isbn13

from django.shortcuts import render
from django.views import generic
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.safestring import mark_safe

from django.contrib.auth.mixins import PermissionRequiredMixin

from django_filters.views import FilterView
from django_tables2 import RequestConfig
from django_tables2.views import SingleTableMixin
from django import forms

from bookshelf.models import books, authors, comments, states
from bookshelf.forms import BookUpdateForm, StateUpdateForm, BookInfoForm
from bookshelf.bookstable import BooksTable, BooksTableFilter, MinimalBooksTable
from bookshelf.authorstable import AuthorsTable, AuthorsTableFilter  # , MinimalAuthorsTable

LOGGER = logging.getLogger(name='mybookdb.bookshelf.librarything')

class PlainTextWidget(forms.Widget):
    def render(self, _name, value, _attrs):
        return mark_safe(value) if value is not None else '-'


class LibraryThingInfoForm(forms.Form):
    """ show info from LibraryThing for selected book """
    title = forms.CharField(max_length=240)
    author_name = forms.CharField()
    author_id = forms.CharField()
    author_url = forms.URLField()
    
    
    def __init__(self , *args, **kwargs):
        book = kwargs.pop('instance') 
        super(LibraryThingInfoForm, self).__init__(*args, **kwargs)      
        assert isinstance(book, books)
        
        if not book.isbn10 and book.isbn13:
            isbn = Isbn13(book.isbn13)
            isbn10 = isbn.convert()
        else:
            isbn10 = book.isbn10
        book_info = self.lookup_book_isbn(isbn10)
        
        # fill form fields
        # self.fields['author_name'].widget = PlainTextWidget()
        self.fields['author_name'].initial = book_info.get('author_name')
        self.fields['author_id'].initial = book_info.get('author_id')
        self.author_url = 'http://www.librarything.com/author/%s' % book_info.get('author_code')
        self.fields['author_url'].initial = self.author_url
        self.fields['title'].initial = book_info.get('title')
        self.fields['title'].widget = forms.Textarea(attrs={'cols': 80, 'rows': 1})
        
        # force fields to be readonly
        for key in self.fields.keys():
            self.fields[key].disabled = True
        
    def lookup_book_isbn(self, isbn):
        result = {}
        headers = {}
        # headers['Accept-Encoding'] = 'application/json'  # is ignored, always get XML
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        headers['User-Agent'] = user_agent
        # title = urllib.parse.quote_plus(book.title)
        # url = 'http://www.librarything.com/title/%s' % title
        # https://www.librarything.com/work/20777649/workdetails
        # apikey = "d231aa37c9b4f5d304a60a3d0ad1dad4"  # API key see LibraryThing wiki
        apikey = os.environ["LIBRARYTHING_APIKEY"]
        baseuri = "http://www.librarything.com/services/rest/1.1/"
        url = f'{baseuri}?method=librarything.ck.getwork&isbn={isbn}&apikey={apikey}'
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            LOGGER.error("lookup on LibraryThing failed: %s" % result)
            assert False, 'TODO handle book lookup failres'
        data_xml = response.text
        data_xml = data_xml.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        #  prevent ValueError: Unicode strings with encoding declaration are not supported
        """ e.g.
<response stat="ok">
    <ltml xmlns="http://www.librarything.com/" version="1.1">
        <item id="20777649" type="work">
            <author id="812768" authorcode="maiwaldstefan">Stefan Maiwald</author>
            <title>Der Knochenraub von San Marco: Roman</title>
            <rating>0</rating>
            <url>http://www.librarything.com/work/20777649</url>
            <commonknowledge/>
        </item>
        <legal>By using this data you agree to the LibraryThing API terms of service.</legal>
    </ltml>
</response>
        """
        ns = '{http://www.librarything.com/}'
        data = etree.fromstring(data_xml)
        assert data.tag == 'response', "expect LibraryThing response"
        assert data.get("stat") == "ok"
        # item = data.find(".//item")
        assert data[0].tag == ns+'ltml'
        item = data[0][0]
        assert item.tag == ns+'item'
        item_id = item.get('id')
        assert item.get('type') == "work"
        for child in item:
            tag_name = child.tag
            if child.tag == ns + 'author':
                # {'id': '812768', 'authorcode': 'maiwaldstefan'}
                result['author_id'] = child.get('id')
                result['author_code'] = child.get('authorcode')
                result['author_name'] = child.text
            elif child.tag == ns +'title':
                result['title'] = child.text
            elif child.tag == ns +'rating':
                result['rating'] = child.text
            elif child.tag == ns +'url':
                lt_url = child.text
            elif child.tag == ns +'commonknowledge':
                pass
            else:
                LOGGER.debug("ignored LibraryThing element %s" % child.tag)
                
        # more info?
        # lt_url +'/reviews'
        # lt_url +'/descriptions'
        # lt_url +'/covers'
        
        # add book to account (login!)
        # http://www.librarything.com/addbook/{item_id}
        return result
        
    def clean(self):
        pass


class LibraryThingInfoView(generic.TemplateView):  # InlineView ?  # TODO needed?
    """ Show book info from LibraryThing. """
    template_name = "bookshelf/librarything_info.html"
    
    
class LibraryThingUpdateView(PermissionRequiredMixin, generic.edit.UpdateView):
    """
    Update book link/state from local bookdb info to LibraryThing.
    """
    model = books  #xxx TODO separate into own table? 
    permission_required = 'bookshelf.can_edit'
    form_class = BookUpdateForm
    
    # TODO to be continued - when API to LibraryThing delivering what we need


class LibraryThingView(generic.TemplateView):
    """ book info from LibraryThing service """
    template_name = "bookshelf/lookup_librarything.html"
    #response_class = TemplateResponse
    #content_type = "text/html"
    
    def get_context_data(self, **kwargs):
        context = super(LibraryThingView, self).get_context_data(**kwargs)
        book = books.objects.get(pk=kwargs['pk'])
        if self.request.POST:
            pass  # book info is read-only
        else:
            # book info from our db
            context['bookinfo_form'] = BookInfoForm(instance=book)
            
            # with matching info from LibraryThing
            context['libraryinfo_form'] = LibraryThingInfoForm(instance=book)
            
            # context['librarything_info'] = Bxxx
        return context
    
    def get_success_url(self): 
        success_url = reverse('book-detail', args=(self.object.id,))
        return success_url
