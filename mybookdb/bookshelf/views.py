"""
views on bookshelf (books, authors, ...)
"""
import logging
import json

from django.shortcuts import render
from django.views import generic
from django.http import HttpResponse, JsonResponse

# from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin

from django_filters.views import FilterView
from django_tables2 import RequestConfig
from django_tables2.views import SingleTableMixin

from bookshelf.models import books, authors, comments, states
from bookshelf.forms import BookUpdateForm
from bookshelf.bookstable import BooksTable, BooksTableFilter, MinimalBooksTable
from bookshelf.authorstable import AuthorsTable, AuthorsTableFilter  # , MinimalAuthorsTable

LOGGER = logging.getLogger(name='mybookdb.bookshelf.views')


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


class BookListGenericView(generic.ListView):  # OBSOLETE
    """
    Generic class-based view for a list of books.
    uses template books_list.html
    """
    model = books
    paginate_by = 25
    
    def get_ordering(self):
        sort = self.request.GET.get('sort', 'title')
        if sort == 'title': 
            ordering = [ 'title' ]
        elif sort == 'updated':
            ordering = [ '-updated' ]
        else:
            ordering = [] # use default / unordered
        return ordering    
    
    
class BooksListTableView(generic.TemplateView):
    """ book list using native bootstrap tables (bootstrap4) """
    template_name = "bookshelf/bookslist_table.html"
    #template_engine = None
    #response_class = TemplateResponse
    #content_type = "text/html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #books_count = books.objects.count()
        #context['books'] = [ books.objects.last() ]
        context['is_paginated'] = False
        return context


def search_book(request):
    query = request.GET
    offset = int(query['offset'])
    limit = int(query['limit'])
    sort_field = query['sort']
    sort_order = query['order']
    if sort_order == 'desc':
        sort_field = '-' + sort_field
    
    qs = books.objects.all()
    
    if query.get('filter'):
        search_filter = {}
        for key, value in json.loads(query['filter']).items():
            if key in ('title',):
                search_filter[key +'__icontains'] = value
            elif key in ('created', 'updated'):
                search_filter[key +'__contains'] = value  # TODO handle date parts
            elif key == 'userRating':
                search_filter["userRating__gte"] = value
            else:
                search_filter[key] = value  # TODO other cols?
        qs = qs.filter(**search_filter)
        
    row_count = qs.count()
    qs = qs.order_by(sort_field)
    data = list(qs.values('id', 'title', 'created', 'updated', 'userRating')[offset:offset+limit])
    result = {
        "total": row_count,
        "rows": data,
    }
    return JsonResponse(result)
    
class BookDetailView(generic.DetailView):
    """
    detail view for a book.
    """
    model = books
    if_paginated = False # KeyError else?
    
    def get_context_data(self, **kwargs):
        context = super(BookDetailView, self).get_context_data(**kwargs)
        context['is_paginated'] = False  # avoid KeyError
        return context 
    
    
class MaintainBooks(PermissionRequiredMixin, generic.View):
    """
    Maintenance of book database.
    """
    def get(self, request, *args, **kwargs):
        # self.object = self.get_object()
        #return super(MaintainBooks, self).get(request, *args, **kwargs)
        raise NotImplementedError("MaintainBooks.get")

    def post(self, request, *args, **kwargs):
        # self.object = self.get_object()
        #return super(MaintainBooks, self).post(request, *args, **kwargs)
        raise NotImplementedError("MaintainBooks.post")
    
    
class BookCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    """
    Create book.
    """
    model = books
    fields = '__all__'
    permission_required = 'bookshelf.can_create'
    
class BookUpdateView(PermissionRequiredMixin, generic.edit.UpdateView):
    """
    Edit book.
    """
    model = books
    permission_required = 'bookshelf.can_edit'
    form_class = BookUpdateForm  # failes with TypeError instance on instantiation
    if_paginated = False # KeyError else?
    
    def __init__(self, *args, **kwargs):
        super(BookUpdateView, self).__init__(*args, *kwargs)

    def get_context_data(self, **kwargs):
        context = super(BookUpdateView, self).get_context_data(**kwargs)
        context['is_paginated'] = False  # avoid KeyError
        return context 
        

class BookDeleteView(PermissionRequiredMixin, generic.edit.DeleteView):
    """
    Delete book.
    """
    model = books
    fields = '__all__'
    permission_required = 'bookshelf.can_delete'

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


def search_author(request):
    query = request.GET
    offset = int(query['offset'])
    limit = int(query['limit'])
    sort_field = query['sort']
    sort_order = query['order']
    if sort_order == 'desc':
        sort_field = '-' + sort_field
    
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
    qs = qs.order_by(sort_field)
    data = list(qs.values('id', 'name',)[offset:offset+limit])  # TODO add  'updated'
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
        context = super().get_context_data(**kwargs)
        authors_count = authors.objects.count()
        #context['authors'] = [ authors.objects.last() ]
        context['is_paginated'] = False
        return context

class AuthorDetailView(generic.DetailView):
    """
    detail view for an author.
    """
    model = authors
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context 


def getAuthorsListDetails(request, pk=None):
    assert pk 
    LOGGER.debug("details for author %s", pk)
    author = authors.objects.get(pk=pk)
    result = []
    author_books = books.objects.filter(authors__id=pk)
    if author_books:
        result.append("<ul>")
        for book_item in author_books:
            desc = book_item.description or ""
            if book_item.userRating:
                # highlight if book has a rating - assume have read
                book_info = "<b>%s</b>" % book_item.title
                book_info += " [%s]" % book_item.userRating
            else:
                book_info = book_item.title
            # TODO date (first, last) from comments
            # TODO status 
            result.append('<li title="%s">%s</li>' % (desc, book_info))
        result.append("</ul>")
    else:
        result.append("<p>no bookes in database</b>")
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

