"""
look book on bookshelf in LibraryThing catalog
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

LT_BASEURL = 'http://www.librarything.com'
LT_NAMESPACE = '{http://www.librarything.com/}'


class PlainTextWidget(forms.Widget):
    def render(self, name, value, attrs):
        return mark_safe(value) if value is not None else '-'


def lookup_book_isbn(book_obj):
    assert isinstance(book_obj, books)
    result = {}
    result['error'] = None
    if not book_obj.isbn10 and book_obj.isbn13:
        isbn = Isbn13(book_obj.isbn13)
        isbn10 = isbn.convert()
    elif book_obj.isbn10:
        isbn10 = book_obj.isbn10
    else:
        raise ValueError('missing book isbn for lookup in LibraryThing')
    
    headers = {}
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    headers['User-Agent'] = user_agent
    apikey = os.environ["LIBRARYTHING_APIKEY"]
    baseuri = LT_BASEURL +"/services/rest/1.1/"
    url = f'{baseuri}?method=librarything.ck.getwork&isbn={isbn10}&apikey={apikey}'
    response = requests.get(url, headers=headers, timeout=30.0)
    if response.status_code != 200:
        LOGGER.error("lookup on LibraryThing failed: %s" % result)
        assert False, 'TODO handle book lookup failures'
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
    ns = LT_NAMESPACE
    data = etree.fromstring(data_xml)
    assert data.tag == 'response', "expect LibraryThing response"
    if data.get("stat") != "ok":
        # e.g. <response stat="fail"><err code="105">Could not determine data ID to retrieve</err></response>
        assert data.get("stat") == "fail"
        err = data.find('err')
        LOGGER.error("failed to lookup book with ISBN %s on LibraryThing:\n%s" 
                     % (isbn, err.text))
        result = {
            'author_id': '',
            'author_code': 'fail',
            'author_name': 'fail, error code=%s' % err.get('code'),
            'title': "%s (%s)" % (err.text, isbn),
        }
        # pass back error
        result['error'] = 'lookup failed (%s) - %s' % (err.get('code'), err.text)
        return result
        
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
    #http://www.librarything.com/work/{book_id}
    # lt_url +'/reviews'
    # lt_url +'/descriptions'
    # lt_url +'/covers'
    result['book_url'] = lt_url

    if result.get('author_code'):
        result['author_url'] = LT_BASEURL +'/author/%s' % result.get('author_code')
    else:
        pass  # TODO guess from author name or search on LT?
    
    # TODO add book to account (login!) - if not added
    # http://www.librarything.com/addbook/{item_id}
    return result


class LibraryThingInfoForm(forms.Form):
    """ show info from LibraryThing for selected book """
    title = forms.CharField(max_length=240)
    author_name = forms.CharField()
    author_id = forms.CharField()
    
    
    def __init__(self , *args, **kwargs):
        book_info = kwargs.pop('book_info') 
        super(LibraryThingInfoForm, self).__init__(*args, **kwargs)      
        
        # force fields to be readonly
        for key in self.fields.keys():
            self.fields[key].disabled = True
            self.fields[key].widget = PlainTextWidget()
        
        # fill form fields
        # self.fields['author_name'].widget = PlainTextWidget()
        self.fields['author_name'].initial = book_info.get('author_name')
        self.fields['author_id'].initial = book_info.get('author_id')
        self.fields['title'].initial = book_info.get('title')
        self.fields['title'].widget = forms.Textarea(attrs={'cols': 80, 'rows': 1})
        
        
    def clean(self):
        pass


#class LibraryThingInfoView(generic.TemplateView):  # InlineView ?  # TODO needed?
#    """ Show book info from LibraryThing. """
#    template_name = "bookshelf/librarything_info.html"
    
    
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
            book_info = lookup_book_isbn(book)            
            form = LibraryThingInfoForm(book_info = book_info)
            context['libraryinfo_form'] = form
            context['book_info'] = book_info
            context['book_url'] = book_info.get('book_url')
            
            if book_info.get('error'):
                # TODO handle and return lookup errors
                pass  # TODO pass error to form message
            
            # TODO fill LibraryThingUpdateView
            
        return context
    
    def get_success_url(self): 
        success_url = reverse('bookshelf:book-detail', args=(self.object.id,))
        return success_url
