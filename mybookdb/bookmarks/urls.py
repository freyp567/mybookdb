"""
bookmarks URL Configuration
"""

from django.urls import path
from django.urls import include, reverse 

from bookmarks import views

app_name = 'bookmarks'

urlpatterns = [
    path('stats/', views.get_bookmarks_stats, name='bookmarks-stats'),
    ]
