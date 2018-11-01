"""bookshelf URL Configuration

"""
# from django.contrib import admin
from django.urls import path
from . import views
from . import catalog_librarything
from django.urls import include, reverse 


urlpatterns = [
    path('', views.index, name='index'),
    #path('books/', views.SimpleBookListView, name='books-v1'),
    path('books/', views.FilteredBookListView.as_view(), name='books'),
    path('books/search/', views.search_book, name='books-search'),
    path('books/v1/', views.BookListGenericView.as_view(), name='books-list'),
    path('books/v2/', views.BooksListTableView.as_view(), name='books-v2'),
    path('books/<int:pk>', views.BookDetailView.as_view(), name='book-detail'),
    path('book/<int:pk>', views.BookDetailView.as_view(), name='book-detail'),
    path('book/<int:pk>/listdetails', views.getBooksListDetails, name='books-list-details'),
    path('books/maintain/', views.MaintainBooks.as_view(), name='maintenance'),
]

urlpatterns += [  
    path('books/create/', views.BookCreateView.as_view(), name='book-create'),
    path('books/<int:pk>/update/', views.BookUpdateView.as_view(), name='book-update'),
    path('books/<int:pk>/delete/', views.BookDeleteView.as_view(), name='book-delete'),
]

urlpatterns += [
    path('book/<int:pk>/state', 
         views.StateUpdateView.as_view(), 
         name='state-update'),
]


urlpatterns += [
    path('book/<int:pk>/librarything>', 
         catalog_librarything.LibraryThingView.as_view(), 
         name='lookup-librarything'),
]

urlpatterns += [
    #path('test/', views.TestView, name='test'),
    #path('authors/', views.AuthorListView.as_view(), name='authors'),
    #path('authors/', views.FilteredAuthorsListView.as_view(), name='authors'),
    path('authors/', views.AuthorsListTableView.as_view(), name='authors'),
    path('authors/search/', views.search_author, name='authors-search'),    
    path('author/<int:pk>', views.AuthorDetailView.as_view(), name='author-detail'),
    path('author/<int:pk>/listdetails', views.getAuthorsListDetails, name='authors-list-details'),
    path('authors_book', views.getAuthors, name='authors_book'),
]
