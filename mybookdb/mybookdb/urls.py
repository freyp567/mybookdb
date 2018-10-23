"""mybookdb URL Configuration

"""
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import url

from django.views.generic import RedirectView

from graphene_django.views import GraphQLView

urlpatterns = [
    path('admin/', admin.site.urls),
]

urlpatterns += [
    path('bookshelf/', include('bookshelf.urls')),
]



# Use static() to add url mapping to serve static files during development (only)
urlpatterns+= static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# Add URL maps to redirect the base URL to our application
urlpatterns += [
    path('', RedirectView.as_view(url='/bookshelf/', permanent=True)),
]



# Django site authentication urls (for login, logout, password management)
urlpatterns += [
    path('accounts/', include('django.contrib.auth.urls')),
]

# for django_select2 ModelWidgets 
# https://django-select2.readthedocs.io/en/latest/get_started.html#installation
# url(r'^select2/', include('django_select2.urls')),

# GraphQL integration
urlpatterns = [
    # ...
    url(r'^graphql', GraphQLView.as_view(graphiql=True)),
]
