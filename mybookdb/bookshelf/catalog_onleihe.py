# -*- coding: latin-1 -*-
"""
lookup book from bookshelf in Onleihe website
"""

import logging
import json
from pathlib import Path
from datetime import datetime

#from pyisbn import Isbn13

from django.views import generic
from django.views.generic.base import View
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone


from django.contrib.auth.mixins import PermissionRequiredMixin

from bookshelf.models import books, onleiheBooks
from bookshelf.forms import BookUpdateForm

from bookshelf.onleihe_client import OnleiheClient, ONLEIHE_DETAIL_FIELDS

LOGGER = logging.getLogger(name='mybookdb.bookshelf.onleihe')


def escape_json(value):
    """ escape json string to pass / embedd as variable in HTML script block """
    # 'Chen, Jade Y'
    value = value.replace('\\r\\n', '\\n')
    value = value.replace('\\n', '\\\\n')
    value = value.replace('"', '\\"')
    return value

def get_cached_details_path(book_obj):
    cached_name = book_obj.isbn13 or book_obj.isbn10 or 'id_%s' % book_obj.id
    cached_name = cached_name +'.json'
    cached_path = Path(__file__).parent / 'static' / 'onleihe'
    cached_path = cached_path / cached_name
    cached_path.resolve()
    return cached_path


def get_cached_details(book_obj):
    cached_path = get_cached_details_path(book_obj)
    if cached_path.exists():
        data = json.loads(cached_path.read_text())
        data = data['details']
        assert len(data) == 1
        details = data[0]
        return details
    return None


def lookup_book_isbn(book_obj):
    assert isinstance(book_obj, books)
    result = {}
    result['error'] = None
    result['updated'] = datetime.now(tz=timezone.utc).isoformat()
    
    # use cached onleihe data to reduce traffic / impact on onleihe site
    cached_path = get_cached_details_path(book_obj)
    if cached_path.exists():
        cached_at = datetime.fromtimestamp(cached_path.stat().st_mtime)
        data = json.loads(cached_path.read_text())
        return data, cached_at
    
    client = OnleiheClient()
    client.connect()
    
    media_info = []
    isbn = '(unknown)'
    if book_obj.isbn13:
        isbn = book_obj.isbn13
        media_info = client.search_book(isbn, 'isbn')
        
    #if not book_obj.isbn10 and book_obj.isbn13:
    #    book_obj.isbn10 = Isbn13(book_obj.isbn13).convert()

    if not media_info:
        # lookup by ISBN not successful, search for book title
        title = book_obj.book_title
        media_info = client.search_book(title, 'title')
        if media_info:
            LOGGER.warning("book not found by isbn but title: %s / '%s'", isbn, book_obj.title)
            result['isbn_notfound'] = book_obj.isbn13
    
    if not media_info:
        LOGGER.warning("book %s not found in Onleihe" % book_obj)
        result['html'] = "not found"
        result['error'] = 'book not found in onleihe'
        add_onleihe_book(book_obj, 'notfound', "book not found in Onleihe")
        result['error'] = 'lookup failed'
        cached_path.write_text(json.dumps(result))
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
                       (len(all_details), book_obj.id, book_obj.title))
        # let user pick if more than one book for searched by title
        
    cached_path.write_text(json.dumps(result))
    return result, None


def add_onleihe_book(book_obj, onleihe_status, comment=""):
    onleihe_book = onleiheBooks(
        book=book_obj,
        status = onleihe_status,
        updated = datetime.now(tz=timezone.utc),
        comment = comment
        )
    onleihe_book.save()
    book_obj.updated = datetime.now(tz=timezone.utc)
    book_obj.save()
    return onleihe_book

    
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
    is_paginated = 0
    
    def post(self, request, pk):
        book_obj = books.objects.get(pk=pk)
        choice = request.POST.get('choice')
        #TODO if more than one book in onleihe, need user to choose one
        if not choice:
            # no book selected, i.e. notfound
            # TODO extra button next to OK to allow to reject
            LOGGER.warning("none of books found in onleihe does match")
            if not hasattr(book_obj, 'onleihebooks'):
                onleihe_book = onleiheBooks(
                    book=book_obj,
                    status = 'notfound',
                    updated = datetime.now(tz=timezone.utc),
                    comment = "none of the books found in onleihe matches"
                    )
                onleihe_book.save()
                book_obj.updated = datetime.now(tz=timezone.utc)
                book_obj.save()
            else:
                onleihe_book = book_obj.onleihebooks
                # TODO need to update?
                
            #result['error'] = 'none of the books found in onleihe matches'
            #TODO how to give feedback?
            context = self.get_context_data(pk=book_obj.id)
            return super(generic.TemplateView, self).render_to_response(context)
        
        # cache onleihe book details in DB
        client = OnleiheClient()
        client.connect()
        if hasattr(book_obj, 'onleihebooks'):
            # already have onleiheBook info assigned, so update it
            onleihe_book = book_obj.onleihebooks
            details = get_cached_details(book_obj)  # TODO option to drop cache to force update
            if not details:
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
                    changed.add(key)
            if changed:
                onleihe_book.save()
                book_obj.updated = datetime.now(tz=timezone.utc)
                book_obj.save()
            else:
                LOGGER.info("no changes for onleihe book info detected for %s" % book_obj.id)
        else:
            media_url = request.POST.get('choice')
            details = get_cached_details(book_obj)
            if not details:
                details = client.get_book_details(media_url)
            onleihe_book = onleiheBooks(
                book=book_obj,
                onleiheId = media_url,
                status = 'confirmed',
                updated = datetime.now(tz=timezone.utc),
                
                )
            CACHE_FIELDS = (  #TODO cleanup fields no longer in use, e.g. pages
                #('bookCoverURL', 'img_cover'),
                #('translator', ''),
                # ('title', ''),
                ('author', ''),
                ('year', ''),
                ('isbn', ''),
                # ('metaKeywords', 'meta-keywords'),
                #('keywords', (self.store_keywords, 'keywords')),
                #('category', (self.store_category, 'category')),
                ('publisher', ''),
                # ('language', ''),
                ('format', ''),
                #('pages', (self.get_pages, 'pages')), #obsolete
                ('length', ''),
                #('allow_copy', (self.is_copy_allowed, 'Kopieren')),
                ('book_description', ''),
                # ('', ''),
            )
            LOGGER.info("updating onleihe related book details for %s" % book_obj.id)
            for tgt_name, from_name in CACHE_FIELDS:
                if not from_name:  # name from is name to
                    from_name = tgt_name
                    value = details.get(tgt_name)
                elif isinstance(from_name, tuple):
                    fn = from_name[0]
                    from_name = from_name[1]
                    value = details.get(from_name)
                    value = fn(value)
                else:
                    value = details.get(from_name)
                if value is None:
                    # e.g. no 'translator' if original book language is german
                    LOGGER.debug("missing value for field %s" % (from_name or tgt_name))
                if from_name == 'author':
                    # TODO fix this, make Array field - currently have Textfield
                    value = ';'.join(value)
                setattr(onleihe_book, tgt_name, value)
                
            onleihe_book.save()
            book_obj.updated = datetime.now()
            if not book_obj.new_description:
                description = onleihe_book.book_description
                now_date = datetime.now(tz=timezone.utc).date()
                description += "\n[from onleihe %s]" % now_date.isoformat()
                book_obj.new_description = description
            book_obj.save()
        
        context = self.get_context_data(pk=book_obj.id)
        return super(generic.TemplateView, self).render_to_response(context)
        
        
    def store_keywords(self, value):
        """ store keywords as comma separated list """
        # sqllite and array valued fields?
        if not value: return None
        return ','.join(value)
    
    def store_category(self, value):
        """ onleihe book category, separate using pipe char """
        if not value: return None
        return '|'.join(value)
    
    def is_copy_allowed(self, value):
        if not value: return None
        return value != 'nicht erlaubt'
        
    def get_pages(self, value):
        if not value: return None
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
            context['onleiheStatus'] = onleiheBook.status
            context['last_update'] = onleiheBook.updated
            context['mustConfirm'] = False
        else:
            onleiheBook = None
            context['onleiheId'] = None
            context['onleiheStatus'] = 'unknown'
            context['last_update'] = '---'
            context['mustConfirm'] = True

        # book info from our db
        context['book'] = book
        context['book_id'] = book.id
        
        if context['onleiheStatus'] in ('notfound',):
            # do not lookup in Onleihe if book could not be found before
            return context            

        if context['onleiheStatus'] not in ('unknown', 'confirmed'):
            LOGGER.debug("search book in Onleihe, status=%s", context['onleiheStatus'])
        
        # with matching info from Onleihe
        try:
            book_info, cached_at = lookup_book_isbn(book)
        except Exception as err:
            LOGGER.exception("lookup in Onleihe not successful - %s", err)
            add_onleihe_book(book, 'lookupfailed', "lookup in Onleihe not successful")
            book_info = {'error': str(err)}
            cached_at = None
        context['cached'] = cached_at
        
        if book_info.get('error'):
            # pass error from lookup to form message handling
            context["messages"] = [book_info.get('error')]
            # TODO indicate warnings, e.g. different ISBN?
            # TODO indicate if cached info used, show date captured == timestamp .json file
        
        context['details'] = []
        context['book_url'] = None
        if book_info.get('details'):
            details = book_info['details']
            context['details'] = details
        
            # transform details into JSON payload for bootstrap-table
            # where the keys are in the first rows, one column per book found
            
            #img_covers = [d['img_cover'] for d in details if 'img_cover' in d]
            book_ids = [d['book_url'].split('/')[-1] for d in details]
            
            if len(details) == 1:  # found one book
                context['onleiheId'] = book_ids[0]
            else:
                LOGGER.info("found multiple books")
                
        else:
            context['details'] = details = []
            
        context["other_books_idx"] = list(range(2, len(details)+1))
        context["details_url"] = reverse('bookshelf:book-detail', args=(book.id,))
        
        return context
    
    def get_success_url(self): 
        success_url = reverse('bookshelf:book-detail', args=(self.object.id,))
        return success_url


class OnleiheDataView(View):
    """ JSON data to fill bootstrap-table """
    id_paginated = False
    
    def get(self, *args, **kwargs):
        book = books.objects.get(pk=kwargs['pk'])
        
        # fetch info from Onleihe
        try:
            book_info, cached_at = lookup_book_isbn(book)
        except Exception as err:
            LOGGER.exception("lookup in Onleihe not successful - %s", err)
            book_info = {'error': str(err)}
        
        if book_info.get('error'):
            LOGGER.error("failed to get book info for onleihe - %s", book_info['error'])
            return JsonResponse({})  # TODO error feedback for bootstrap table
        
        table_data = []
        if book_info.get('details'):
            details = book_info['details']
        
            # transform details into JSON payload for bootstrap-table
            # where the keys are in the first rows, one column per book found
            
            img_covers = [d['img_cover'] for d in details if 'img_cover' in d]
            book_ids = [d['book_url'].split('/')[-1] for d in details]
            
            if len(details) == 1:  # found one book
                onleiheId = book_ids[0]
                LOGGER.debug("found book in onleihe: %s", onleiheId)
            else:
                LOGGER.info("found multiple books in onleihe: %s", book_ids)
                
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
                    if value is None:
                        LOGGER.warning("missing field %s", field_name)
                        continue
                    if field_name == 'book_url':
                        if img_covers and len(img_covers) > pos:
                            value = [value, img_covers[pos]]
                        else:
                            value = [value, '']
                        if hasattr(book, 'onleihebooks'):
                            onleihe_updated = book.onleihebooks.updated
                        else:
                            onleihe_updated = None
                        if cached_at is not None:
                            if onleihe_updated is None:
                                updated = cached_at.date()
                            else:
                                updated = min(onleihe_updated, cached_at.date())
                        else:
                            updated = onleihe_updated
                        value.append(updated and updated.strftime("%Y-%m-%d") or "new")
                    if field_name in ('title','book_description'):
                        if '"' in value:
                            # causes troubles with python -> javascript -> bootstrap-table
                            # while loading html: Uncaught SyntaxError: Unexpected identifier
                            # as for display only, map them
                            value = value.replace('"', "'")
                    if field_name == 'author':
                        value = ', '.join(value)
                    row['book%s' % (pos+1)] = value or ''
                    
                    #if onleiheBook:
                    #    # TODO determine where differences between details item and onleiheBook
                table_data.append(row)
                
        else:
            table_data = []
            
        return JsonResponse(table_data, safe=False)
