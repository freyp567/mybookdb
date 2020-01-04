"""
timeline URL Configuration
"""

from django.urls import path
from django.urls import include, reverse 

from timeline import views

app_name = 'timeline'

urlpatterns = [
    path('timeline/', views.TimelineView.as_view(), name='get-timeline'),
    path('<int:pk>/show', views.BookEventListView.as_view(), name='show-timeline'),
    path('<int:pk>/create', views.BookEventCreateView.as_view(), name='add-event'),
    path('<int:book_id>/event/<int:pk>/delete', views.BookEventDeleteView.as_view(), name='delete-event'),
    ]
