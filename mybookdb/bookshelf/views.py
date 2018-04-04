from django.shortcuts import render
from django.views import generic
from django_filters.views import FilterView
from django_tables2 import RequestConfig
from django_tables2.views import SingleTableMixin

from .models import books, authors, comments, states
from .bookstable import BooksTable, BooksTableFilter


def index(request):
    """
    view home page
    """
    num_books = books.objects.all().count()
    num_authors = authors.objects.all().count()
    
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


class FilteredBookListView(SingleTableMixin, FilterView):
    # TODO -- test, experienced troubles with django-filter and bootstrap3/4 compatiblity
    table_class = BooksTable 
    model = books
    template_name = 'bookshelf/books_table_filtered.html'
    filterset_class = BooksTableFilter
        


class BookListGenericView(generic.ListView):
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
    Generic class-based detail view for a book.
    """
    model = books
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context 
    
    
class AuthorListView(generic.ListView):
    """
    Generic class-based list view for a list of authors.
    """
    model = authors
    paginate_by = 25


class AuthorDetailView(generic.DetailView):
    """
    Generic class-based detail view for an author.
    """
    model = authors
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context 
    