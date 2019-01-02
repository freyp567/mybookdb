import json
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


def get_bookmarks_stats(request):
    author_links_count = author_links.object.count()
    book_links_count = book_links.object.count()
    stats = {
        'author_links': author_links_count,
        'book_links': book_links_count,
    }
    return JsonResponse(stats)

def get_linkname_from_path(path):
    pathsteps = path.split('/')
    name = pathsteps.pop()
    while not name.strip(): 
        # empty if url endswith '/', e.g. for lovelybooks.de
        name = pathsteps.pop()
    orig_name = name
    if name.endswith('.html'):
        name = name[:-5]
    if '%' in name:  # URL encoded?
        name = urllib.parse.unquote(name)
    if name.startswith('mediaInfo,0-0-'):
        # for onleihe-regio
        name = name[14:]
        while name.endswith('-0'):
            name = name[:-2]
            
    return name
    
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
        assert path, "missing path in URL"
        name = get_linkname_from_path(path)
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

    def get_success_url(self):
        # success_url = reverse('bookmarks:bookmark-show', args=(self.kwargs['objtype'], self.object.id,))
        if self.kwargs['objtype'] == 'authors':
            success_url = reverse('bookshelf:author-detail', args=(self.kwargs['pk'],))
        else:
            success_url = reverse('bookshelf:book-detail', args=(self.kwargs['pk'],))
        # TODO return to referer ?
        return success_url
    
    def get_initial(self):
        initial_data = super(BookmarkCreate, self).get_initial()
        return initial_data
    
    def get_form_kwargs(self):
        kwargs = super(BookmarkCreate, self).get_form_kwargs()
        kwargs['objtype'] = self.kwargs['objtype']
        kwargs['pk'] = self.kwargs['pk']
        return kwargs

    def form_valid(self, form):
        # TODO assign bookmark to author / book
        # django.db.utils.IntegrityError: NOT NULL constraint failed: bookmarks_author_links.author_id
        obj_type = self.kwargs['objtype']
        obj_id = self.kwargs['pk']
        if obj_type == 'authors':
            obj = authors.objects.get(pk=obj_id)
            #form.instance.author_links = obj
            ## django.db.utils.IntegrityError: NOT NULL constraint failed: bookmarks_author_links.author_id
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
        return context
    