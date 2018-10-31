"""
table view of authors

using django-tables2, see https://github.com/jieter/django-tables2

"""

from django.urls import reverse 
from django.utils.html import format_html
from django.template.defaultfilters import striptags
from django import forms

import django_filters
import django_tables2 as tables

from .models import authors


class AuthorsFilterForm(forms.Form):
    
    name = forms.CharField(label='Name', max_length=20) # verbose_name='Author Name'

    # [ f.name for f in authors.get_fields() ]
    # ['comments', 'googleBookId', 'grBookId', 'reviews', 'states', 'id', 'isbn10', 'isbn13', 'title', 'binding', 'description', 'numberOfPages', 'publisher', 'publicationDate', 'reviewsFetchedDate', 'offersFetchedDate', 'grRating', 'grRatingsCount', 'subject', 'created', 'updated', 'userRating', 'lentToName', 'lentToUri', 'thumbnailSmall', 'thumbnailLarge', 'amazonBookId', 'authors']

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_valid(self):
        """Return True if the form has no errors, or False otherwise."""
        #return self.is_bound and not self.errors
        return True
                
        

class AuthorsTableFilter(django_filters.FilterSet):
    
    name = django_filters.CharFilter(label='name', lookup_expr='icontains')
    
    class meta:
        model = authors
        #form = AuthorsFilterForm 

    
        
class IDColumn(tables.Column):
    
    def render(self, value):
        # generate link to book details
        url = reverse('author-detail', args=[str(value)])
        idhtml = '<a target="author-detail" href="%s">%s</a>' % (url, value)
        return format_html(idhtml)
    
    
class MinimalAuthorsTable(tables.Table):
    
    class Meta:
        model = authors 
        #template_name = 'django_tables2/bootstrap.html'
        

class AuthorsTable(tables.Table):
    
    id = IDColumn()
    name = tables.Column(visible=True)
    lowerCaseName = tables.Column(visible=False)
    familyName = tables.Column(visible=False)
    
    class Meta:
        model = authors
        #template_name = 'authorshelf/Authors_table.html'
        
        
    #def render_description(self, value):
    #    return '<span title="%s">(description)</span>' % "TODO title"
    
    def render_created(self, value):
        if value is None:
            return ""
        return value.strftime("%Y-%m-%d")
    
    def render_updated(self, value):
        if value is None:
            return ""
        return value.strftime("%Y-%m-%d")
