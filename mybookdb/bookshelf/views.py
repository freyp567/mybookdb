# -*- coding: utf-8 -*-
"""
views on bookshelf (books, authors, ...)
"""
import logging
import json
from datetime import datetime


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


class HttpResponseTemporaryRedirect(HttpResponse):
    status_code = 307

    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = iri_to_uri(redirect_to)
        

def index(request):
    """
    view home page
    """
    num_books = books.objects.all().count()
    num_authors = authors.objects.all().count()
    LOGGER.debug("index num_books=%s num_authors=%s", num_books, num_authors)
    
    return render(
        request,
        'index.html',
        context={'num_books':num_books, 'num_authors':num_authors,}
    )


def SimpleBookListView(request):
    """ simple list of books """
    queryset = books.objects.all()
    #filterset = BooksTableFilter() # cannot use in place of queryset: no attribute _default_manager
    table = BooksTable(queryset)
    #table.orderBy = '-'
    #table.paginate(page=request.GET.get('page', 1), per_page=25)
    RequestConfig(request, paginate={'per_page': 12}).configure(table)
    return render(request, 'bookshelf/books_table.html', {'books_table': table})


class FilteredBookListView(SingleTableMixin, FilterView):
    """ list view for books with filtering support """
    table_class = BooksTable
    model = books
    template_name = 'bookshelf/books_table_filtered.html'
    filterset_class = BooksTableFilter
    ordering = '-created'


class BookListGenericView(generic.ListView):
    """
    Generic class-based view for a list of books.
    uses template books_list.html
    
    used for Book List, /bookshelf/books/v1/?sort=
    """
    model = books
    paginate_by = 25

    def get_queryset(self):  # disables ordering
        """ overloaded to implement custom sort orders """
        ordering = self.get_ordering()
        qs = books.objects.all()  
        #TODO if not authenticated:
        #qs = qs.filter('states__private'=False)
        if ordering:
            if isinstance(ordering, str):
                LOGGER.info("sort book list by custom sort order: %s", ordering)
                if ordering == 'wishlist':
                    # map ordering to what can be handled by DB
                    ordering = ['states__toBuy', 'userRating', '-updated']
                    qs = qs.filter(states__haveRead=False, states__toBuy=True)
                elif ordering == 'onleihe_unkown':
                    ordering = ['states__toBuy', 'userRating', '-updated']
                    qs = qs.filter(onleihebooks=None)
                elif ordering == 'missing_timeline':
                    ordering = [ '-updated' ]
                    qs = qs.filter(timelineevent__isnull=True, states__haveRead=True)
                elif ordering == 'reading':
                    ordering = [ '-updated' ]
                    qs = qs.filter(states__readingNow=True)
                else:
                    ordering = (ordering,)
            qs = qs.order_by(*ordering)
        return qs
    
    def get_context_data(self, *args, **kwargs):
        data = super(BookListGenericView, self).get_context_data(*args, **kwargs)
        data["result_count"] = len(self.object_list)
        return data
    
    def get_ordering(self):
        sort = self.request.GET.get('sort', 'updated')
        if sort == 'title': 
            ordering = [ 'title' ]
        elif sort == 'created':
            ordering = [ '-created' ]
        elif sort == 'updated':
            ordering = [ '-updated' ]
        elif sort in ('reading', 'wishlist', 'onleihe_unkown', 'missing_timeline'):
            ordering = sort  # mapped by get_queryset
        else:
            LOGGER.info("book list unsorted, sort=%s", sort)
            ordering = [] # use default / unordered
        return ordering    
    
    
class BooksListTableView(generic.TemplateView):
    """ book list using native bootstrap tables (bootstrap4) """
    template_name = "bookshelf/bookslist_table.html"
    
    def get_context_data(self, **kwargs):
        context = super(BooksListTableView, self).get_context_data(**kwargs)
        #books_count = books.objects.count()
        #context['last_book'] = [ books.objects.last() ]
        if not 'is_paginated' in context:
            context['is_paginated'] = False
            # SET TO avoid. ValueError: invalid literal for int() with base 10: 'is_paginated'
        book_states = {
            "haveRead": "have read",
            "haveRead+favorite": "have read/+",
            "readingNow": "reading",
            "toBuy": "want read/wishlist",
            "iOwn": "unfinished",
            "obsolete": "obsolete",
            "private": "private",
            "other": "other",
            #"": "not read",
        }
        # if logged in / role is ...
        book_states["private"] = "private"
        
        context['book_states'] = json.dumps(book_states);
        return context

    
def currently_reading(request):  ## experimental
    to_url = reverse('bookshelf:books-list')
    to_url += '?sort=reading'
    return redirect(to_url)

                      

def search_book(request):
    query = request.GET
    sort_field = query['sort']
    sort_order = query['order']
    if sort_order == 'desc':
        sort_field = '-' + sort_field

    if query.get('filter'):
        search_filter = json.loads(query['filter'])
    else:
        search_filter = None
        
    return search_book_filtered(request, sort_field, search_filter)
    
    
def search_book_filtered(request, sort_field, filter=None):
    query = request.GET
    offset = int(query.get('offset', '0'))
    limit = int(query.get('limit', '0'))
    
    LOGGER.debug("search_book query=%s" % query)
    qs = books.objects.all()
    
    qs = qs.select_related("states")
    if filter:
        search_filter = {}
        for key, value in filter.items():
            if key in ('title',):
                search_filter[key +'__icontains'] = value
            elif key in ('created', 'updated'):
                search_filter[key +'__contains'] = value  # TODO handle date parts
            elif key == 'userRating':
                search_filter["userRating__gte"] = value
            elif key == 'state':
                if value == 'haveRead':
                    search_filter["states__haveRead"] = True
                elif value == 'haveRead+favorite':
                    cond = Q(states__haveRead=True) & Q(states__favorite=True)
                    qs = qs.filter(cond)
                elif value == 'readingNow':
                    search_filter["states__readingNow"] = True
                elif value == 'iOwn':  # unfinished
                    search_filter["states__iOwn"] = True                    
                elif value == 'not_read':
                    cond =Q(states_haveRead=False) & Q(states_readingNow=False)
                    qs = qs.filter(cond)
                elif value == 'toBuy':  # want read
                    search_filter["states__toBuy"] = True
                elif value == 'private':
                    search_filter["states__private"] = True
                elif value == 'obsolete':
                    search_filter["states__obsolete"] = True
                elif value == 'other':
                    cond = Q(states__haveRead=False) 
                    cond &= Q(states__readingNow=False)
                    cond &= Q(states__iOwn=False)
                    cond &= Q(states__toBuy=False)
                    cond &= Q(states__toRead=False)
                    cond &= Q(states__obsolete=False)
                    qs = qs.filter(cond)
                else:
                    LOGGER.warn("unrecognized filter value for vield state: %s" % value)
            else:
                search_filter[key] = value  # TODO other cols?
        if search_filter:
            qs = qs.filter(**search_filter)
        
    row_count = qs.count()
    qs = qs.order_by(sort_field)
    qs = qs[offset:offset+limit]
    data = []
    fields = (
        'id', 'title', 'unified_title', 'created', 'updated', 'userRating', 
        'states__haveRead', 'states__readingNow', 'states__toRead', 'states__toBuy', 'states__iOwn',
        'states__obsolete', 'isbn13'
    )
    nodata = object()
    for row in qs.values(*fields):
        row_data = {}
        for field_name in fields:
            if field_name.startswith('states__'):
                value = row.get(field_name)
                # lookup display title for state
            elif field_name == 'title':
                value = row.get('unified_title') or row.get('title')
            else:
                value = row.get(field_name, nodata)
                if value is nodata:
                    value = '---'
            row_data[field_name] = value
        state_obj = states.objects.get(pk=row['id'])
        row_data['state_conflict'] =  state_obj.state_conflict
        row_data['orig_title'] =  row.get('title')
        data.append(row_data)
        
    result = {
        "total": row_count,
        "rows": data,
    }
    return JsonResponse(result)
    
class BookDetailView(generic.DetailView):
    """
    detail view for a book.
    template: books_detail.html
    """
    model = books
    if_paginated = False # KeyError else
    # form see book_details.html
    
    def get_context_data(self, **kwargs):
        context = super(BookDetailView, self).get_context_data(**kwargs)
        context['is_paginated'] = False  # avoid KeyError
        book_comments = self.object.comments_set.all()
        book_comments = book_comments.order_by('-dateCreatedInt')
        context['books_comments'] = book_comments
        context['comment_now'] = datetime.now().strftime("%Y-%m-%dT%H:%M")
        try:
            events = timelineevent.objects.filter(book=self.object)
            event_count = events.count()
        except Exception:
            event_count = "??"
        context['event_count'] = event_count
        return context 
    
class MaintainBooks(PermissionRequiredMixin, generic.View):
    """
    Maintenance of book database.
    """
    def get(self, request, *args, **kwargs):  # TODO should not override
        # self.object = self.get_object()
        #return super(MaintainBooks, self).get(request, *args, **kwargs)
        raise NotImplementedError("MaintainBooks.get")

    def post(self, request, *args, **kwargs):  # TODO should not override
        # self.object = self.get_object()
        #return super(MaintainBooks, self).post(request, *args, **kwargs)
        raise NotImplementedError("MaintainBooks.post")
    
    
class BookCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    """
    Create book.
    """
    permission_required = 'bookshelf.can_create'
    model = books
    form_class = BookCreateForm
    
    def get_initial(self):
        initial_data = super(BookCreateView, self).get_initial()
        return initial_data
 
    def get_context_data(self, **kwargs):
        if getattr(self, 'object', None) is None:
            # avoid AttributeError: 'BookCreateView' object has no attribute 'object'
            self.object = None 
        context = super(BookCreateView, self).get_context_data(**kwargs)
        context['tag'] = "div"
        return context

    def post(self, request, *args, **kwargs):
        # super(BookCreateView, self).post(*args, **kwargs)
         form = self.get_form()
         if form.is_valid():
             metrics.books_count.inc()
             return self.form_valid(form)
         else:
             return self.form_invalid(form)


# @method_decorator(csrf_exempt, name='dispatch')
class BookEditableUpdate(generic.UpdateView):  # PermissionRequiredMixin
    """
    handles update requests from list of books (bootstap-table / editable plugin)
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(BookEditableUpdate, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        return self.update(request, **kwargs)
    
    def update(self, request, **kwargs):
        return JsonResponse({
            'status': 'error',
        'msg': 'FAIL!'})


class BookUpdateView(PermissionRequiredMixin, generic.edit.UpdateView):
    """
    Edit details of book.
    """
    model = books
    permission_required = 'bookshelf.can_edit'
    form_class = BookUpdateForm
    is_paginated = False
    
    def __init__(self, *args, **kwargs):
        super(BookUpdateView, self).__init__(*args, *kwargs)

    def get_context_data(self, **kwargs):
        context = super(BookUpdateView, self).get_context_data(**kwargs)
        context['is_paginated'] = False  # avoid KeyError
        context['tag'] = "div"
        return context 
        

class BookDeleteView(PermissionRequiredMixin, generic.edit.DeleteView):
    """
    Delete book.
    """
    model = books
    fields = '__all__'
    permission_required = 'bookshelf.can_delete'


class StateUpdateView(PermissionRequiredMixin, generic.edit.UpdateView):
    """
    Edit book state.
    invoked from book detail view / button "Update Book State"
    """
    model = states
    permission_required = 'bookshelf.can_edit'
    form_class = StateUpdateForm
    
    def __init__(self, *args, **kwargs):
        self.book_obj = None
        super(StateUpdateView, self).__init__(*args, *kwargs)

    def _get_book(self, book_id):
        assert book_id is not None, "book unknown"
        book_obj = books.objects.get(pk=book_id)
        if book_obj is None:
            LOGGER.error("missing book for state: %s", book_id)
            raise Http404(_("No book found for book_id=%(book_id)s") % 
                          {'book_id': book_id})
        return book_obj
        
    def get(self, request, *args, **kwargs):
        book_id =kwargs.get('pk')
        self.book_obj = self._get_book(book_id)
        if not self.book_obj.has_states(): 
            # new books and books imported do not have a state obj assigned, auto-create
            states_obj = states(pk=book_id)
            states_obj.book = self.book_obj
            states_obj.save()
        else:
            # ATTN ensure pk / id and book_id to be equal
            others = states.objects.filter(book_id = self.book_obj.pk)
            others = [obj for obj in others if obj.pk != book_id]
            if others:
                raise ValueError("detected states %s for book %s" % ([obj.pk for obj in others], book_id))

        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        book_id = kwargs.get('pk')
        self.book_obj = self._get_book(book_id)
        self.object = states.objects.get(pk=book_id)
        form = self.get_form()
        if form.is_valid():
            if self.object.haveRead:
                # TODO fixthis will update count everytime status is edited - independend if changed or not
                # state haveRead True before? form.changed_data / .cleaned_data
                metrics.books_read_count.inc()
            else:
                LOGGER.debug("update book %s state %s", book_id, self.object) 
                pass
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_form_kwargs(self):  # TODO cleanup after debugging
        kwargs = super(StateUpdateView, self).get_form_kwargs()
        # {'initial': {}, 'prefix': None, 'instance': <states: 5132 (favorite haveRead)>}
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(StateUpdateView, self).get_context_data(**kwargs)
        if self.request.POST:
            # if "cancel" in request.POST:
            pass  # book info is read-only
        else:
            # context['bookinfo_form'] = BookInfoForm(instance=self.book_obj)  # TODO refactor this
            pass
        return context
    
    def get_success_url(self):
        success_url = reverse('bookshelf:book-detail', args=(self.object.id,))
        return success_url
    
    
class AuthorListView(generic.ListView):
    """
    list of authors.
    uses template authors_list.html
    """
    model = authors
    paginate_by = 25

    def get_ordering(self):
        sort = self.request.GET.get('sort', 'name')
        if sort == 'name': 
            ordering = [ 'name' ]
        elif sort == 'updated':
            ordering = [ '-updated' ]
        else:
            ordering = [] # use default / unordered
        return ordering    

def author_obj_to_dict(obj):
    data = {}
    for key in ('id', 'name', 'latest_book', 'updated', 'last_book_update', 
                'book_rating_avg', 'book_count', 'books_read'):
        data[key] = getattr(obj, key)
    return data

def search_author(request):
    query = request.GET
    offset = int(query['offset'])
    limit = int(query['limit'])
    sort_field = query['sort']
    sort_order = query['order']
    
    LOGGER.debug("search_author query=%s" % query)
    qs = authors.objects.all()
    
    if query.get('filter'):
        search_filter = {}
        for key, value in json.loads(query['filter']).items():
            if key in ('name',):
                search_filter[key +'__icontains'] = value
            else:
                search_filter[key] = value  # TODO other cols?
        qs = qs.filter(**search_filter)
        
    row_count = qs.count()
    if sort_field == 'book_count':
        qs = qs.annotate(book_count_agg=Count('books'))
        sort_field = 'book_count_agg'
    elif sort_field == 'books_read':
        qs = qs.annotate(
            book_read_agg=Count('books',
                                 filter=Q(books__states__haveRead=True)))
        sort_field = 'book_read_agg'
    elif sort_field == 'last_book_update':
        qs = qs.annotate(
            last_bk_upd_agg=Max('books__updated'))
        sort_field = 'last_bk_upd_agg'
    elif sort_field == 'book_rating_avg':
        qs = qs.annotate(
            book_rating_avg_agg=Avg('books__userRating'))
        sort_field = 'book_rating_avg_agg'
        
    if sort_order == 'desc':
        sort_spec = '-' + sort_field
    else:
        sort_spec = sort_field
        
    qs = qs.order_by(sort_spec)
    data = [ author_obj_to_dict(obj) for obj in qs[offset:offset+limit] ]
    result = {
        "total": row_count,
        "rows": data,
    }
    return JsonResponse(result)
        
class FilteredAuthorsListView(SingleTableMixin, FilterView):  # old
    """ list of authors with filtering """
    table_class = AuthorsTable
    model = authors
    template_name = 'bookshelf/authors_table_filtered.html'
    filterset_class = AuthorsTableFilter

class AuthorsListTableView(generic.TemplateView):
    """ book list using native bootstrap tables (bootstrap4) """
    template_name = "bookshelf/authors_table.html"
    
    def get_context_data(self, **kwargs):
        context = super(AuthorsListTableView, self).get_context_data(**kwargs)
        authors_count = authors.objects.count()
        context['authors_count'] = authors_count
        context['is_paginated'] = False  # ???
        return context


class AuthorsCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    """
    add new author
    """
    permission_required = 'bookshelf.can_create'
    model = authors
    form_class = AuthorCreateForm

    def get_success_url(self): 
        success_url = reverse('bookshelf:author-detail', args=(self.object.id,))
        return success_url


class AuthorUpdateView(PermissionRequiredMixin, generic.edit.UpdateView):
    """
    update author details
    """
    permission_required = 'bookshelf.can_create'
    model = authors
    form_class = AuthorUpdateForm

    def get_initial(self):
        initial_data = super(AuthorUpdateView, self).get_initial()
        return initial_data
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
    def get_success_url(self): 
        success_url = reverse('bookshelf:author-detail', args=(self.object.id,))
        return success_url


class AuthorDetailView(generic.DetailView):
    """
    detail view for an author.
    """
    model = authors

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['short_bio'] = self.object.short_bio or ''
        
        authors_books = books.objects.filter(authors__id = self.object.id)
        authors_books = authors_books.order_by('-created')
        context['is_paginated'] = False
        books_read = list(authors_books.filter(states__haveRead = True))
        context['books_read'] = books_read
        other_books = [ book for book in authors_books if book not in books_read ]
        context['books_other'] = other_books
        
        return context 



def getBooksListDetails(request, pk=None):
    """ detail view row for bootstrap-table """
    assert pk
    LOGGER.debug("details for book %s", pk)
    book = books.objects.get(pk=pk)
    result = []
    book_authors = authors.objects.filter(books__id=pk)
    if book_authors:
        author_names = []
        for author in book_authors:
            author_names.append(author.name)
        if len(author_names) > 1:
            result.append("Authors: %s" % ", ".join(author_names))
        else:
            result.append("Author: %s" % ", ".join(author_names))
            
    description = book.new_description or book.orig_description
    if description:
        if result:
            result.append("")
        result.append("<p>%s</p>" % description)
    comment_info = []
    qs_comments = comments.objects.filter(book__id = pk).order_by('dateCreatedInt')
    for comment in qs_comments:
        comment_text = comment.text
        if len(comment_text) > 80:
            comment_text = comment_text[:80] +'...'
        comment_created = comment.dateCreated.date().isoformat()
        if comment_created in comment_text:
            comment_info.append('<span class="bookcomment-small">%s</span>' % 
                                comment_text)
        else:
            comment_info.append('<span class="bookcomment-small">%s  %s</span>' % 
                                (comment_created, comment_text))
        if len(comment_info) > 5:
            comment_info.append('...')
            break
    if comment_info:
        book_comments = "%s" % '<br>'.join(comment_info)
        # if result: 
        #    result.append('<hr/>')
        result.append(book_comments)
    html = '\n'.join(result)
    return HttpResponse(content=html)


def getAuthorsListDetails(request, pk=None):
    assert pk 
    LOGGER.debug("details for author %s", pk)
    author = authors.objects.get(pk=pk)
    result = []
    author_books = books.objects.filter(authors__id=pk).order_by('-updated')
    if author_books:
        result.append("<ul>")
        for book_item in author_books:
            comment_info = []
            qs_comments = comments.objects.filter(book__id = book_item.id).order_by('dateCreatedInt')
            for comment in qs_comments:
                comment_text = comment.text
                if len(comment_text) > 80:
                    comment_text = comment_text[:80] +'...'
                comment_created = comment.dateCreated.date().isoformat()
                if comment_created in comment_text:
                    comment_info.append('<span class="bookcomment-small">%s</span>' % 
                                        comment_text)
                else:
                    comment_info.append('<span class="bookcomment-small">%s  %s</span>' % 
                                        (comment_created, comment_text))
                if len(comment_info) > 1:
                    comment_info.append('...')
                    break
            book_info = ''
            book_title = "<b>%s</b>" % book_item.book_title
            book_details_url = reverse('bookshelf:book-detail', args=(book_item.id,))
            book_title = '<a target="details" href="%s">%s</a>' % (book_details_url, book_title)
            if book_item.userRating:
                # highlight if book has a rating - assume have read
                book_info += "<b>%s</b>" % book_title
                book_info += " [Rating: %s]" % book_item.userRating
            else:
                book_info += book_title
                book_info += " [no rating]"
            if comment_info:
                book_info += '<br>'
                book_info += '<br>'.join(comment_info)
            # TODO status 
            desc = book_item.new_description or book_item.description or ""
            bs_tooltip = 'class="book_tooltip" data-toggle="tooltip" data-html="true" '
            result.append('<li %s title="%s">%s</li>' % (bs_tooltip, desc, book_info))
        result.append("</ul>")
    else:
        result.append("<p>note: have no books in db for given author</b>")
    html = '\n'.join(result)
    return HttpResponse(content=html)

def getAuthors(request):
    term = request.GET['term']
    filtered_authors = authors.objects.filter(name__icontains = term)
    data = []
    for obj in filtered_authors:
        if not obj.id: 
            continue 
        data.append({
            "id": str(obj.id),
            "text": obj.name or str(obj.id)
        })
    LOGGER.debug("getAuthors found for '%s': %s objects", term, len(data))
    # https://select2.org/data-sources/formats
    results = {"results": data, "pagination": {"more": False}}
    #return JsonResponse(results, safe=False)
    return HttpResponse(json.dumps(results), content_type="application/json;charset=utf-8")


def createUpdateBookStatus(request, pk):
    book_obj = books.objects.get(pk=pk)
    if not hasattr(book_obj, 'states'):
        states_obj = states.objects.create(book=book_obj)
        states_obj.save()
    else:
        states_obj = book_obj.states
    
    to_url = reverse('bookshelf:status-update', args=(states_obj.id,))
    if request.POST:
        # forward POST request
        return HttpResponseTemporaryRedirect(to_url)
    else:
        return redirect(to_url)


class UpdateBookComment(PermissionRequiredMixin, generic.edit.UpdateView):
    
    permission_required = 'bookshelf.can_edit'    
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UpdateBookComment, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        try:
            book_id = kwargs['pk']
            comment_id = request.POST['pk']
            new_text = request.POST['value']
            return self.save(book_id, comment_id, new_text)
        except BaseException:
            LOGGER.exception("update comment failed id=%s" % comment_id)
            return HttpResponseBadRequest('update failed')
    
    def save(self, book_id, comment_id, new_text):
        now = datetime.now(tz=timezone.utc)
        book_obj = books.objects.get(pk=book_id)
        if comment_id == '0':  # new comment
            comment_obj = comments()
            comment_obj.book = book_obj
            comment_obj.bookTitle = book_obj.book_title
            comment_obj.dateCreatedInt = int(now.timestamp() *1000)
            comment_obj.dateCreated = now
            book_obj.updated = now
            comment_obj.save()            
            book_obj.save()
        else:
            comment_obj = comments.objects.get(pk=comment_id)
            assert comment_obj.book_id == book_obj.id, "wrong book id"
            
        if comment_obj.text != new_text:
            if not new_text:
                comment_obj.delete()
            else:
                comment_obj.text = new_text
                comment_obj.save()
            return HttpResponse('updated')
        else:
            LOGGER.info("comment unchanged id=%s value='%s'" % (comment_id, new_text))
            return HttpResponse('unchanged')
    

    
class BookStatusUpdateView(SuccessMessageMixin, PermissionRequiredMixin, generic.edit.UpdateView):
    """
    Edit book status.
    """
    #xxx TODO vs StateUpdateView
    model = states
    permission_required = 'bookshelf.can_edit'
    # form_class = BookStatusUpdateForm
    template_name = 'bookshelf/bookstatus_update.html'
    form_class = StateUpdateForm
    
    def __init__(self, *args, **kwargs):
        super(BookStatusUpdateView, self).__init__(*args, *kwargs)

    def get_success_url(self):
        success_url = reverse('bookshelf:book-status-update', args=(self.object.id,))
        return success_url
    
    def get_success_message(self, cleaned_data):
        return _('Status updated for book %(book_title)s') % {'book_title': self.object.book.book_title}

    def get_context_data(self, **kwargs):
        context = super(BookStatusUpdateView,
                        self).get_context_data(**kwargs)
        #context['is_paginated'] = False  # avoid KeyError
        if self.request.POST:
            # if "cancel" in request.POST:
            pass  # book info is read-only
        else:
            context['bookinfo_form'] = BookInfoForm(instance=self.object.book)        
        if not 'non_field_errors' in context:
            context['non_field_errors'] = []
        return context 



class BookUserRatingUpdate(generic.UpdateView):  # PermissionRequiredMixin
    """
    handles update requests from userrating editable
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(BookUserRatingUpdate, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        book_id = kwargs['pk']
        if book_id == 0:
            # when called from bookslist cell / field col-rating, have id in POST data
            book_id = request.POST['pk']
            
        rating = request.POST['value']
        return self.update(request, book_id, rating)
    
    def update(self, request, book_id, rating):
        try:
            rating_value = int(rating)
            assert rating_value > 0 and rating_value <= 5, "bad rating value %s" % repr(rating)
            LOGGER.info("update userRating for book_id=%s to %s", book_id, rating_value)
            book_obj = books.objects.get(pk=book_id)
            book_obj.userRating = rating_value
            book_obj.updated = datetime.now(tz=timezone.utc)
            book_obj.save()
        except BaseException:
            LOGGER.exception("update userRating failed")
            return HttpResponseBadRequest('update FAILED')
        else:
            return HttpResponse('updated')
