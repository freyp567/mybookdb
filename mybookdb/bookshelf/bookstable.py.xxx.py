"""
table view of books

using django-tables2, see https://github.com/jieter/django-tables2

"""

from django.urls import reverse 
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.template.defaultfilters import striptags
from django import forms

import django_filters
import django_tables2 as tables

from mybookdb.models import books


class BooksFilterForm(forms.Form):
    
    title = forms.CharField(label='Title', max_length=20) # verbose_name='Book Title'

    # [ f.name for f in books.get_fields() ]
    # ['comments', 'googleBookId', 'grBookId', 'reviews', 'states', 'id', 
    #  'isbn10', 'isbn13', 'title', 'binding', 'description', 'numberOfPages', 
    #  'publisher', 'publicationDate', 'reviewsFetchedDate', 'offersFetchedDate', 
    #  'grRating', 'grRatingsCount', 'subject', 'created', 'updated', 'userRating', 
    #  'lentToName', 'lentToUri', 'thumbnailSmall', 'thumbnailLarge', 
    #  'amazonBookId', 'authors',
    # ]

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_valid(self):
        """Return True if the form has no errors, or False otherwise."""
        #return self.is_bound and not self.errors
        return True
                
        

class BooksTableFilter(django_filters.FilterSet):
    
    title = django_filters.CharFilter(label='title', lookup_expr='icontains')
    # TODO author
    userRating_gt = django_filters.NumberFilter(label='Rating', field_name='userRating', lookup_expr='gt')
      # TODO field width smaller for Rating
    
    class meta:
        model = books
        #form = BooksFilterForm 

    
        
class IDColumn(tables.Column):
    
    def render(self, value):
        # generate link to book details
        url = reverse('bookshelf:book-detail', args=[str(value)])
        idhtml = '<a target="book-detail" href="%s">%s</a>' % (url, value)
        return format_html(idhtml)
    
    
class DescriptionColumn(tables.Column):
    """ value is computed from new_description / old_description 
    through book model property description
    """
    
    def __init__(self):
        super().__init__(orderable=False) #, empty_values=())
        
    def render(self, value):
        if not value: 
            value = ''
        short_desc = value[:80]
        short_desc = striptags(short_desc)
        if len(value) > 80:
            value += '...'
        value = value.replace('<br/>', '\n')
        value = striptags(value)
        return format_html('<span title="%s">%s</span>' % (value, short_desc))
    
    
class DateColumn(tables.Column):

    def __init__(self, accessor, verbose_name=None, default=None):
        super().__init__(orderable=True, 
                         #accessor=accessor,
                         verbose_name = verbose_name, 
                         #localize=??? 
                         empty_values = (),
                         default = default)
        self.classname = "date_column"
    
    def render(self, value):
        # https://eric.sau.pe/custom-column-widths-in-bootstrap-tables/
        # https://stackoverflow.com/questions/4457506/set-the-table-column-width-constant-regardless-of-the-amount-of-text-in-its-cell
        # https://stackoverflow.com/questions/19847371/django-how-to-change-the-column-width-in-django-tables2
        value = striptags(value)
        return mark_safe("<div class='" + self.classname + "' >" +value+"</div>")

    
class MinimalBooksTable(tables.Table):
    
    class Meta:
        model = books 
        #template_name = 'django_tables2/bootstrap.html'
        

class BooksTable(tables.Table):
    
    id = IDColumn()
    isbn10 = tables.Column(visible=False)
    isbn13 = tables.Column(visible=False)
    title = tables.Column(orderable=True)
    unified_title = tables.Column(visible=False)
    book_serie = tables.Column(visible=False)
    binding = tables.Column(visible=False)
    orig_description = tables.Column(visible=False)
    new_description = tables.Column(visible=False)
    description = tables.Column(visible=False)
    created = DateColumn("created", verbose_name="Created", )
    updated = DateColumn("updated", verbose_name="Updated", default="(not set)")
    numberOfPages = tables.Column(verbose_name="#", visible=False)
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
    sync_mybookdroid = tables.DateColumn(verbose_name="Synced")
    bookCatalogueId = tables.Column(visible=False)
    
    # TODO show authors
    
    class Meta:
        model = books
        template_name = 'django_tables2/bootstrap4.html'
        
        
    #def render_description(self, value):
    #    return '<span title="%s">(description)</span>' % "TODO title"
    
    #def render_author(xxx):
    # TODO implement
    
    #def render_created(self, value):
    #    if value is None:
    #        return ""
    #    value = value.strftime("%Y-%m-%d")
    #    return mark_safe("<div class='date_column' >" +value+"</div>")
    
    def render_updated(self, value):
        if value is None:
            return ""
        value = value.strftime("%Y-%m-%d")
        return mark_safe("<div class='date_column' >" +value+"</div>")
