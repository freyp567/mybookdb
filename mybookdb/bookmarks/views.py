import json
import re
import urllib.parse 
from datetime import datetime

from django.shortcuts import render
from django.views import generic
from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError, transaction
from django.urls import reverse

from bookshelf.models import books, authors 

from bookmarks.models import author_links, book_links, linksites, linksites_url
from bookmarks.forms import BookmarkCreateForm

import logging
LOGGER = logging.getLogger(name='mybookdb.bookmarks.views')


def get_bookmarks_stats(request):
    author_links_count = author_links.object.count()
    book_links_count = book_links.object.count()
    stats = {
        'author_links': author_links_count,
        'book_links': book_links_count,
    }
    return JsonResponse(stats)

def get_linkname_from_path(path, site, query):
    pathsteps = path.split('/')
        
    name = pathsteps.pop().strip()
    while pathsteps and not name: 
        # empty if url endswith '/', e.g. for lovelybooks.de
        name = pathsteps.pop()
        name = name.strip()
    orig_name = name

    if not name:
        name = site
        if name.startswith('www.'):
            name = name[4:]
            
        for suffix in ('.com', '.de'):
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name
    
    if name.endswith('.html'):
        name = name[:-5]
    if '%' in name:  # URL encoded?
        name = urllib.parse.unquote(name)
    if name.startswith('mediaInfo,0-0-'):
        # for onleihe-regio
        name = name[14:]
        while name.endswith('-0'):
            name = name[:-2]

    if site == "mybookdb":
        if '/author/' in path:
            return "author-%s" % name
        elif '/book/' in path:
            return "book-%s" % name
        else:
            return "mybookdb-%s" % name
        
    linkname = None            
    if site.endswith('.onleihe.de'):
        linkname = 'onleihe-' + name
    elif site =='books.google.de':
        linkname = 'googlebooks'
        if 'id=' in query:
            query = query.split('id=')[1]
            query = query.split('&')[0]
            if query:
                linkname +='-' + query
            
    elif 'wikipedia.org' in site:
        linkname = 'wikipedia-' + name
    elif 'goodreads.com' in site:        
        linkname = 'gr-' +name
    elif site == 'www.audible.de':
        linkname = 'audible-' + name
    elif site == 'www.amazon.de':
        linkname = 'amazon-' + name
    elif site =='www.evernote.com':
        parts = name.split('-')
        assert len(parts) == 5 and len(parts[4]) == 12, "evernote.com, unexpected name '%s'" % name
        linkname = 'evernote-' + parts[4]
    elif site == 'www.youtube.com':
        match =re.match('v=(?P<youtube_id>[0-9A-Za-z]+).*', query)
        if match is not None:
            linkname = 'youtube-' + match.group('youtube_id')
        else:
            LOGGER.warning("failed to extract youtube_id from query '%s'", query)
    else:
        # 'verlorene-werke.blogspot.com', *.wordpress.com, ...
        linkname = None
        
    if linkname is None:
        if len(name) > 50:
            LOGGER.debug("use shortened default name='%s' for link site='%s'", name, site)
            linkname = name[:50] +'..'
        else:
            LOGGER.debug("use default name='%s' for link site='%s'", name, site)
            linkname = name
    return linkname
    
def parse_uri(request):
    # e.g. https://de.wikipedia.org/wiki/Aharon_Appelfeld
    uri = request.GET['uri']
    info = {
        'site': '',
        'site_id': '',
        'name': '',
        'site_created': False,
    }
    
    if uri:
        parts = urllib.parse.urlparse(uri)
        if parts.scheme not in ('http', 'https'):
            raise ValueError("bad protocol %s" % hosts[0])
        site = parts.netloc
        assert site, "missing host part in URL"
        path = parts.path
        if not path:
            assert path, "missing path in URL"

        if parts.netloc == request.get_host():
            site = 'mybookdb'
        
        name = get_linkname_from_path(path, site, parts.query)
        nurl = urllib.parse.urlsplit(uri)
        npath = nurl.geturl()
        qs = None
        while nurl.path:
            qs = linksites_url.objects.filter(url=npath)
            if qs:
                break
            npath = npath[:npath.rfind('/')]
            nurl = urllib.parse.urlsplit(npath)
                
            
        if not qs:
            qs = linksites_url.objects.filter(url=npath)
            
        if not qs:
            # new site, auto-register
            try:
                with transaction.atomic():
                    site = linksites.objects.create(name=site, base_url=npath)
                    link = linksites_url.objects.create(site=site, url=npath)
                    info['site_created'] = True  # TODO insert into droplist, autoselect
                    site_id = site.id
                    site = site.name
            except IntegrityError:
                raise
                
        else:
            assert len(qs) == 1, 'expect linsites_url.url to be unique'
            site_link = qs.first()
            site = site_link.site.name
            site_id = site_link.site.id
            
        info['site'] = site
        info['site_id'] = site_id
        info['name'] = name
        
        
    return JsonResponse(info)


def show_bookmark(request, objtype, pk):
    request = request
    return HttpResponse('TODO show_bookmarks')


class BookmarkCreate(generic.edit.CreateView):  # TODO fix permissions -- declarative
    """
    Create bookmark.
    """
    #permission_required = 'bookshelf.can_create'
    template_name = "bookmarks_form.html"
    form_class = BookmarkCreateForm
    
    def __init__(self, *args, **kwargs):
        super(BookmarkCreate, self).__init__(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        #if request.POST.get('cancel_button'):
        #    request = request  # TODO how to handle crispy-from cancel button proberly?
        return super(BookmarkCreate, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # success_url = reverse('bookmarks:bookmark-show', args=(self.kwargs['objtype'], self.object.id,))
        if self.kwargs['objtype'] == 'authors':
            success_url = reverse('bookshelf:author-detail', args=(self.kwargs['pk'],))
        else:
            success_url = reverse('bookshelf:book-detail', args=(self.kwargs['pk'],))
        return success_url
    
    def get_form_kwargs(self):
        kwargs = super(BookmarkCreate, self).get_form_kwargs()
        kwargs['objtype'] = self.kwargs['objtype']
        kwargs['pk'] = self.kwargs['pk']
        kwargs['host'] = self.request.get_host()
        return kwargs

    def form_valid(self, form):
        # assign bookmark to author / book
        obj_type = self.kwargs['objtype']
        obj_id = self.kwargs['pk']
        if obj_type == 'authors':
            obj = authors.objects.get(pk=obj_id)
        elif obj_type == 'books':
            obj = books.objects.get(pk=obj_id)
        else:
            assert False, "unsupported objtype '%s'" % obj_type
            
        obj.updated = datetime.now()
        obj.save()
        return super(BookmarkCreate, self).form_valid(form)
 
    def get_context_data(self, **kwargs):
        obj_type = self.kwargs['objtype']
        obj_id = self.kwargs['pk']
        if obj_type == 'authors':
            target_obj = authors.objects.get(pk=obj_id)
            title = target_obj.name
            objtype = 'author'
        elif obj_type == 'books':
            target_obj = books.objects.get(pk=obj_id)
            title = target_obj.title
            objtype = 'book'
        else:
            assert False, "unsupported objtype '%s'" % obj_type
        
        kwargs['target_obj'] = target_obj
        context = super(BookmarkCreate, self).get_context_data(**kwargs)
        context['objtype'] = obj_type
        context['title'] = title
        context['is_paginated'] = False
        context['tag'] = context.get('tag') or 'div'  # missing tag ...
        return context
    
    
class BookmarkDeleteView(generic.DeleteView):
    """
    delete Bookmark
    """
    permission_required = 'bookshelf.can_create'
    template_name = 'bookmark_confirm_delete.html'

    def __init__(self, *args, **kwargs):
        super(BookmarkDeleteView, self).__init__(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        # ask to confirm delete request
        return super().get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
       return super().delete(request, *args, **kwargs)

    def get_bookmark_source(self):
        """ get author or book for bookmark """
        obj_type =self.kwargs['objtype']
        obj_id =self.kwargs['pk']
        
        if obj_type == 'authors':
            obj = authors.objects.get(pk=obj_id)
        elif obj_type =='books':
            obj = books.objects.get(pk=obj_id)
        else:
            raise NotImplementedError("unsupported %s" % obj_type)
        return obj

    def get_bookmark_source_title(self):
        """ get descriptive title for source of bookmark (author nane, book title, ...) """
        obj_type =self.kwargs['objtype']
        obj_id =self.kwargs['pk']
        
        if obj_type == 'authors':
            obj = authors.objects.get(pk=obj_id)
            title = obj.name
        elif obj_type =='books':
            obj = books.objects.get(pk=obj_id)
            title = obj.book_title
        else:
            raise NotImplementedError("unsupported %s" % obj_type)
        return title

    def get_bookmark_object(self):
        obj_type =self.kwargs['objtype']
        obj_id =self.kwargs['pk']
        link_id =self.kwargs['link_id']
        # self.get_context_object_name()
        if obj_type == 'authors':
            obj = authors.objects.get(pk=obj_id)
            link = obj.author_links.get(pk=link_id)
        elif obj_type =='books':
            obj = books.objects.get(pk=obj_id)
            link = obj.book_links.get(pk=link_id)        
        else:
            raise NotImplementedError("unsupported %s" % obj_type)
        return link


    def get_object(self, queryset=None):
        return self.get_bookmark_object()

    def get_context_data(self, *args, **kwargs):
        """ update context dict """
        context = super().get_context_data(*args, **kwargs)
        context['source'] = self.get_bookmark_source()
        context['source_title'] = self.get_bookmark_source_title()
        context['bookmark'] = self.object
        return context

    def get_success_url(self): 
        if self.kwargs['objtype'] == 'authors':
            success_url = reverse('bookshelf:author-detail', args=(self.kwargs['pk'],))
        else:
            success_url = reverse('bookshelf:book-detail', args=(self.kwargs['pk'],))
        return success_url
