from django.shortcuts import render
from django.views import generic

from .models import books, authors, comments, states


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


class BookListView(generic.ListView):
    """
    Generic class-based view for a list of books.
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
    