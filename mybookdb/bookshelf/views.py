from django.shortcuts import render
from django.views import generic
#from django.views.generic.edit import CreateView, UpdateView, DeleteView

from django_filters.views import View, FilterView
from django_tables2 import RequestConfig
from django_tables2.views import SingleTableMixin

from .models import books, authors, comments, states
from .forms import BookUpdateForm
from .bookstable import BooksTable, BooksTableFilter, MinimalBooksTable
from .authorstable import AuthorsTable, AuthorsTableFilter  # , MinimalAuthorsTable

# from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin

import logging

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
        context={'num_books':num_books,'num_authors':num_authors,}
    )


def SimpleBookListView(request):
    queryset = books.objects.all()
    #filterset = BooksTableFilter() # cannot use in place of queryset: no attribute _default_manager
    table = BooksTable(queryset)
    #table.orderBy = '-'
    #table.paginate(page=request.GET.get('page', 1), per_page=25)
    RequestConfig(request, paginate={'per_page': 12}).configure(table)
    return render(request, 'bookshelf/books_table.html', {'books_table': table})


def TestView(request):
    book_fields = [ f.name for f in books._meta.get_fields() ]
    LOGGER.debug("TestView fields=%s", book_fields)
    form = BooksTableFilter({}, books.objects.all()).form
    assert len(form.fields) > 0, "missing form fields"
    return render(request, 'test.html', {'form': form})
    

class FilteredBookListView(SingleTableMixin, FilterView):
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
    
    
class BookDetailView(generic.DetailView):
    """
    detail view for a book.
    """
    model = books
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context 
    
    
class MaintainBooks(PermissionRequiredMixin, View):
    """
    Maintenance of book database.
    """
    def get(self, request, *args, **kwargs):
        # self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # self.object = self.get_object()
        return super().post(request, *args, **kwargs)
    
    
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
    
#class BookUpdateView(generic.FormView):  # PermissionRequiredMixin, 
    #"""
    #Edit book.
    #"""
    #model = books
    #permission_required = 'bookshelf.can_edit'
    #template_name = 'bookshelf/books_form.html'
    #form_class = BookUpdateForm
    
    ##def form_valid(self, form):
        ##context = self.get_context_data() 
        ###...
    
class BookDeleteView(PermissionRequiredMixin, generic.edit.DeleteView):
    """
    Delete book.
    """
    model = books
    fields = '__all__'
    permission_required = 'bookshelf.can_delete'
    
    
class AuthorListView(generic.ListView):
    """
    Generic class-based list view for a list of authors.
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


class FilteredAuthorsListView(SingleTableMixin, FilterView):
    table_class = AuthorsTable
    model = authors
    template_name = 'bookshelf/authors_table_filtered.html'
    filterset_class = AuthorsTableFilter


class AuthorDetailView(generic.DetailView):
    """
    Generic class-based detail view for an author.
    """
    model = authors
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context 
    