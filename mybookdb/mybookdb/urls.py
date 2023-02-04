"""mybookdb URL Configuration

"""
from django.contrib import admin
from django.urls import path, include
#from mybookdb.settings import DEBUG
from mybookdb.views import error_404

from django.conf import settings
from django.conf.urls import handler404
from django.conf.urls.static import static
from django.urls import re_path

from django.views.generic import RedirectView

# from graphene_django.views import GraphQLView  # not yet adapted to Django 4.0
import django_prometheus

favicon_view = RedirectView.as_view(url='/static/favicon.ico', permanent=True)

handler404 = error_404  # 'mybooksdb.views.error_404'


urlpatterns = [
    re_path(r'^favicon\.ico$', favicon_view),
    path('admin/', admin.site.urls),
]

if settings.USE_DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),

        # For django versions before 2.0:
        # re_path(r'^__debug__/', include(debug_toolbar.urls)),

    ] + urlpatterns    

urlpatterns += [
    path('bookshelf/', include('bookshelf.urls', namespace="bookshelf")),
    path('bookmarks/', include('bookmarks.urls', namespace="bookmarks")),
    path('timeline/', include('timeline.urls', namespace="timeline")),
]


# Use static() to add url mapping to serve static files during development (only)
urlpatterns+= static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# Add URL maps to redirect the base URL to our application
urlpatterns += [
    path('', RedirectView.as_view(url='/bookshelf/', permanent=True), name=''),
]


# Django site authentication urls (for login, logout, password management)
urlpatterns += [
    path('accounts/', include('django.contrib.auth.urls')),
]

# for django_select2 ModelWidgets 
# https://django-select2.readthedocs.io/en/latest/get_started.html#installation
# re_path(r'^select2/', include('django_select2.urls')),

## GraphQL integration
## note: showing GraphiQL only for non-production environment (if DEBUG is True)
#urlpatterns += [
#    path(r'graphql', GraphQLView.as_view(graphiql=False)),
#    path(r'graphiql', GraphQLView.as_view(graphiql=True)),
#]

urlpatterns += [
    # url('^prometheus/', include('django_prometheus.urls')),
    re_path('', include('django_prometheus.urls')),
]