"""
bookmarks URL Configuration
"""

from django.urls import path
from django.urls import include, reverse 

from bookmarks import views

app_name = 'bookmarks'

urlpatterns = [
    path('stats/', views.get_bookmarks_stats, name='bookmarks-stats'),
    path('<slug:objtype>/<int:pk>/create/', views.BookmarkCreate.as_view(), name='bookmark-create'),
    path('<slug:objtype>/<int:pk>/show/', views.show_bookmark, name='bookmark-show'),
    path('<slug:objtype>/<int:pk>/delete/<int:link_id>/', views.BookmarkDeleteView.as_view(), name='delete-bookmark'),
    
    # delete-bookmark
    
    path('parse_uri', views.parse_uri, name='parse_uri'),
    ]
