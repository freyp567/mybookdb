"""bookshelf URL Configuration

"""
# from django.contrib import admin
from django.urls import path
from . import views
from django.urls import include


urlpatterns = [
    path('', views.index, name='index'),
    #path('books/', views.SimpleBookListView, name='books-v1'),
    path('books/', views.FilteredBookListView.as_view(), name='books'),
    path('books/search/', views.search_book, name='books-search'),
    path('books/v1/', views.BookListGenericView.as_view(), name='books-list'),
    path('books/v2/', views.BooksListTableView.as_view(), name='books-v2'),
    path('books/<int:pk>', views.BookDetailView.as_view(), name='book-detail'),
    path('books/maintain/', views.MaintainBooks.as_view(), name='maintenance'),
]

urlpatterns += [  
    path('books/create/', views.BookCreateView.as_view(), name='book-create'),
    path('books/<int:pk>/update/', views.BookUpdateView.as_view(), name='book-update'),
    path('books/<int:pk>/delete/', views.BookDeleteView.as_view(), name='book-delete'),
]

urlpatterns += [
    #path('test/', views.TestView, name='test'),
    #path('authors/', views.AuthorListView.as_view(), name='authors'),
    path('authors/', views.FilteredAuthorsListView.as_view(), name='authors'),
    path('author/<int:pk>', views.AuthorDetailView.as_view(), name='author-detail'),
]
