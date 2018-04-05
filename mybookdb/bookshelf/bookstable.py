"""
table view of books

using django-tables2, see https://github.com/jieter/django-tables2

"""

from django.urls import reverse 
from django.utils.html import format_html
from django.template.defaultfilters import striptags
from django import forms

import django_filters
import django_tables2 as tables

from .models import books


class BooksFilterForm(forms.Form):
    
    title = forms.CharField(label='Title', max_length=20) # verbose_name='Book Title'

    # [ f.name for f in books.get_fields() ]
    # ['comments', 'googleBookId', 'grBookId', 'reviews', 'states', 'id', 'isbn10', 'isbn13', 'title', 'binding', 'description', 'numberOfPages', 'publisher', 'publicationDate', 'reviewsFetchedDate', 'offersFetchedDate', 'grRating', 'grRatingsCount', 'subject', 'created', 'updated', 'userRating', 'lentToName', 'lentToUri', 'thumbnailSmall', 'thumbnailLarge', 'amazonBookId', 'authors']

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_valid(self):
        """Return True if the form has no errors, or False otherwise."""
        #return self.is_bound and not self.errors
        return True
                
        

class BooksTableFilter(django_filters.FilterSet):
    
    title = django_filters.CharFilter(label='title', lookup_expr='icontains')
    userRating_gt = django_filters.NumberFilter(label='Rating', name='userRating', lookup_expr='gt')
    #userRating_lt = django_filters.NumberFilter(label='Rating(lt)', name='userRating', lookup_expr='lt')
    
    class meta:
        model = books
        # TODO description (html stripped)
        # TODO authors
        #fields = {
        #    'title': ['exact', 'contains'],
        #    'description': ['icontains'],
        #    'userRating': ['gt', 'lt'],
        #}
        #form = BooksFilterForm 

    
        
class IDColumn(tables.Column):
    
    def render(self, value):
        # generate link to book details
        url = reverse('book-detail', args=[str(value)])
        idhtml = '<a target="book-detail" href="%s">%s</a>' % (url, value)
        return format_html(idhtml)
    
    
class DescriptionColumn(tables.Column):
    
    def __init__(self):
        super().__init__(orderable=False)
        
    def render(self, value):
        short_desc = value[:80]
        short_desc = striptags(short_desc)
        if len(value) > 80:
            value += '...'
        value = value.replace('<br/>', '\n')
        value = striptags(value)
        return format_html('<span title="%s">%s</span>' % (value, short_desc))
    
    
class MinimalBooksTable(tables.Table):
    
    class Meta:
        model = books 
        #template_name = 'django_tables2/bootstrap.html'
        

class BooksTable(tables.Table):
    
    id = IDColumn()
    isbn10 = tables.Column(visible=False)
    isbn13 = tables.Column(visible=False)
    title = tables.Column()
    binding = tables.Column(visible=False)
    description = DescriptionColumn()
    created = tables.Column(verbose_name="EntryCreated")
    numberOfPages = tables.Column(verbose_name="#")
    publisher = tables.Column(visible=False)
    publicationDate = tables.Column(visible=False)
    offersFetchedDate = tables.Column(visible=False)
    reviewsFetchedDate = tables.Column(visible=False)
    grRating = tables.Column(visible=False)
    grRatingsCount = tables.Column(visible=False)
    subject = tables.Column(visible=False)
    userRating = tables.Column(visible=True, verbose_name="Rating")
    amazonBookId = tables.Column(visible=False)
    lentToName = tables.Column(visible=False)
    lentToUri = tables.Column(visible=False)
    thumbnailSmall = tables.Column(visible=False)
    thumbnailLarge = tables.Column(visible=False)
    
    # TODO show authors
    # TODO hide description - rather show as tooltip
    
    class Meta:
        model = books
        #template_name = 'bookshelf/books_table.html'
        
        
    #def render_description(self, value):
    #    return '<span title="%s">(description)</span>' % "TODO title"
    
    #def render_author(xxx):
    # TODO implement
    
    def render_created(self, value):
        if value is None:
            return ""
        return value.strftime("%Y-%m-%d")
    
    def render_updated(self, value):
        if value is None:
            return ""
        return value.strftime("%Y-%m-%d")
