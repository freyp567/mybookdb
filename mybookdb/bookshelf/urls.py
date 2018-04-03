"""bookshelf URL Configuration

"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    #path('books/', views.BookListGenericView.as_view(), name='books'),
    path('books/', views.SimpleBookListView, name='books'),
    #path('books/', views.FilteredBookListView.as_view(), name='books'),
    path('books/<int:pk>', views.BookDetailView.as_view(), name='book-detail'),
    path('authors/', views.AuthorListView.as_view(), name='authors'),
    path('author/<int:pk>', views.AuthorDetailView.as_view(), name='author-detail'),
]

