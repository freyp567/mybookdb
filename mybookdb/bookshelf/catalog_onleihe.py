"""
lookup book from bookshelf in Onleihe website
"""

import os
import logging
import json
import requests
import http.client
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

from bookshelf.models import books, authors, comments, states
from bookshelf.forms import BookUpdateForm, StateUpdateForm, BookInfoForm
from bookshelf.bookstable import BooksTable, BooksTableFilter, MinimalBooksTable
from bookshelf.authorstable import AuthorsTable, AuthorsTableFilter  # , MinimalAuthorsTable

LOGGER = logging.getLogger(name='mybookdb.bookshelf.onleihe')

ONLEIHE_HOST = 'www.onleihe.de'
#ONLEIHE_BASEURL = 'http://www.onleihe.de'
ONLEIHE_BASEURL = 'http://www4.onleihe.de'



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
        raise ValueError('missing book isbn for lookup in Onleihe')
    
    headers = {}
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'
    headers['User-Agent'] = user_agent
    #url = ONLEIHE_BASEURL +'/onleiheregio/frontend/myBib,0-0-0-100-0-0-0-0-0-0-0.html'
    
    #conn = http.client.HTTPSConnection(ONLEIHE_HOST)
    #conn.request("GET", '/onleiheregio/frontend/login,0-0-0-0-0-0-0-0-0-0-0.html')
    #response = conn.getresponse()
    
    #url = ONLEIHE_BASEURL +'/onleiheregio/frontend/myBib,0-0-0-100-0-0-0-0-0-0-0.html'
    url = ONLEIHE_BASEURL +'/onleiheregio/frontend/login,0-0-0-0-0-0-0-0-0-0-0.html'
    response = requests.get(url)
    cookies = response.headers.get("Set-Cookie")
    if cookies:
        ck = cookies.split(';')
        
    # select Onleihe biblio 
    url = ONLEIHE_BASEURL +'/onleiheregio/frontend/login,0-0-0-0-0-0-0-0-0-0-0.html'
    headers['Content-Type'] = "application/x-www-form-urlencoded"
    response = requests.post(url, data='cmdId=800&libraryId=411&Weiter=Weiter', headers=headers)
    cookies = response.headers.get("Set-Cookie")
    if cookies:
        ck = cookies.split(';')
    
    cookie = 'FESLIBID=NDEx'
    headers['Cookie'] = cookie
    url = ONLEIHE_BASEURL +'/onleiheregio/frontend/search,0-0-0-0-0-0-0-0-0-0-0.html'
    response = requests.get(url, headers=headers)
    assert response.status_code == 200, "onleihe not reachable?"
    # html = response.text 
    cookies = response.headers.get("Set-Cookie")
    if cookies:
        ck = cookies.split(';')
        # add JSESSONID to cookie
        cookie += '; ' +ck[0]
    #Cookie: JSESSIONID=8A80BC69606A4DB6BF1C19FBF8032D48.vs11308n3; FESLIBID=NDEx; NewLogaholic_VID=108140310991; NewLogaholic_SESSION=53557563076; _ga=GA1.2.401254113.1525934352
    cookie += '; _ga=GA1.2.254826237.1541237449'
    cookie += '; _gid=GA1.2.1604980323.1541237449'
    headers['Cookie'] = cookie
    headers['Origin'] = ONLEIHE_BASEURL
    headers['Cache-Control'] = "max-age=0"
    headers['Referer'] = "http://www4.onleihe.de/onleiheregio/frontend/search,0-0-0-0-0-0-0-0-0-0-0.html"
    headers['Content-Type'] = "application/x-www-form-urlencoded"
    #headers['Upgrade-Insecure-Requests'] = "1"
    """
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8" 
    -H "Accept-Encoding: gzip, deflate" 
    -H "Accept-Language: en-US,en;q=0.9,de-DE;q=0.8,de;q=0.7" 
    -H "Cookie: JSESSIONID=5484285A100DF7A559449E39CD49288B.vs11308n3; NewLogaholic_VID=108140310991; NewLogaholic_SESSION=333909064; _ga=GA1.2.254826237.1541237449; _gid=GA1.2.1604980323.1541237449" 
    """
    url = ONLEIHE_BASEURL +"/onleiheregio/frontend/search,0-0-0-0-0-0-0-0-0-0-0.html"

    # while debugging, send request to httpbin.org
    # url = "http://httpbin.org"
    #url = "http://192.168.188.27:8083"
    
    #data = f'cmdId=701^&sK=1000^&pText=^&pTitle=^&pAuthor=^&pKeyword=^&pisbn={isbn10}&ppublishdate=^&pMediaType=-1^&pLang=-1^&pPublisher=-1^&pCategory=-1^&SK=1000^&pPageLimit=20^&Suchen=Suchen'
    data = f'cmdId=701^&sK=1000^&pText=^&pTitle=Rosenthal&pAuthor=^&pKeyword=^&pisbn=^&ppublishdate=^&pMediaType=-1^&pLang=-1^&pPublisher=-1^&pCategory=-1^&SK=1000^&pPageLimit=20^&Suchen=Suchen'
    # TODO make sure to handle properly
    response = requests.post(url, headers=headers, data=data, timeout=30.0)
    if response.status_code != 200:
        # http://192.168.188.27:8083
        LOGGER.error("lookup on Onleihe failed: %s" % response.text)
        assert False, 'TODO handle book lookup failures'
    data_html = response.text
    if "Ein unerwarteter Fehler ist aufgetreten" in data_html:
        """ e.g.
        <div class="m-row">	
            <div class="item-1">&nbsp;</div>			
            <div class="item-2"><p>Ein unerwarteter Fehler ist aufgetreten! Bitte versuchen Sie es ...	
            </p></div>
        """
        result['html'] = data_html  # TODO extract error relevant portion
        result['error'] = 'unexpected error'
        return result
    
    # TODO determine page url for book(s) found and extract info using GDOM
    """
    <a class="anchor" title="Details zum Titel: Die Akte Rosenthal - Teil 1" 
    href="mediaInfo,0-0-539763720-200-0-0-0-0-0-0-0.html">
	Details <span class="hidden">zum Titel: Die Akte Rosenthal - Teil 1</span></a>    
    """
    #if 'mediaInfo,' not in data_html:
    #    LOGGER.warning("no media items found")
    #else:
    media_info = []
    for match in re.finditer('<a (.*?)>(.*?)</a>', data_html):
        anchor = match.group(0)
        if 'mediaInfo' in anchor:
            media_info.append(anchor)  # TODO extract media id
        else:
            LOGGER.debug("link ignored: %s" % anchor)
        
    if media_info:
        LOGGER.info("search found %s mediaInfo items" % len(media_info))
    assert False, "TODO to be implemented"
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
    
    def get_context_data(self, **kwargs):
        context = super(OnleiheView, self).get_context_data(**kwargs)
        book = books.objects.get(pk=kwargs['pk'])
        if self.request.POST:
            pass  # book info is read-only
        else:
            # book info from our db
            context['bookinfo_form'] = BookInfoForm(instance=book)
            
            # with matching info from LibraryThing
            book_info = lookup_book_isbn(book)            
            context['book_info'] = book_info
            context['book_url'] = book_info.get('book_url')
            
            if book_info.get('error'):
                # TODO handle and return lookup errors
                pass  # TODO pass error to form message
            
            # TODO fill OnleiheUpdateView
            
        return context
    
    def get_success_url(self): 
        success_url = reverse('book-detail', args=(self.object.id,))
        return success_url
