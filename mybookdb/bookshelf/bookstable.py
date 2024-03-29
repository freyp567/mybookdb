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
from django_filters.views import FilterView

import django_tables2 as tables
from django_tables2.views import SingleTableMixin

from .models import books


class IDColumn(tables.Column):
    
    def render(self, value):
        # generate link to book details
        url = reverse('bookshelf:book-detail', args=[str(value)])
        idhtml = '<a target="book-detail" href="%s">%s</a>' % (url, value)
        return format_html(idhtml)

    
class MinimalBooksTable(tables.Table):
    
    class Meta:
        model = books 
        #template_name = 'django_tables2/bootstrap.html'
        #fields = ()
        

class BooksTable(tables.Table):
    
    id = IDColumn()
    title = tables.Column(orderable=True)
    authors = tables.Column(verbose_name="Authors")
    created = tables.Column(verbose_name="Created")
    updated = tables.Column(verbose_name="Updated")
    read_start = tables.Column(verbose_name="Start Reading")
    read_end = tables.Column(verbose_name="Finished")
    sync_mybookdroid = tables.Column(verbose_name="Sync")
    userRating = tables.Column(verbose_name="Rating")
    
    max_length = 38
    
    class Meta:
        model = books
        template_name = 'django_tables2/bootstrap4.html'
        fields = ('id', 'title', 'authors', 'userRating', 'created', 'updated', 'read_start', 'read_end', 'synced')

    def render_title(self, record):
        if record.unified_title:
            if record.book_serie:
                value = "%s - %s" % (record.unified_title, record.book_serie)
            else:
                value = record.unified_title
        else:
            value = record.title
        if not value: 
            value = '(unknown)'
        shortened = value[:self.max_length]
        shortened = striptags(shortened)
        if len(value) > self.max_length:
            shortened += '...'
        value = value.replace('<br/>', '\n')
        value = striptags(value)
        return format_html('<span title="%s">%s</span>' % (value, shortened))
        
    def value_authors(self, record):
        authors = set()
        for obj in record.authors.all():
            authors.add(obj.name)
        if not authors:
            return ""
        return ", ".join(authors)
        
    def render_authors(self, record):
        authors = set()
        for obj in record.authors.all():
            authors.add(obj.name)
        if not authors:
            return ""
        values = ["<div class='author_name' >%s</div>" % n.replace(' ', '&nbsp;') for n in authors]
        return mark_safe("<br/>".join(values))

    def render_isodate(self, column, value):
        if value is None:
            return "---"
        value = value.strftime("%Y-%m-%d")
        return mark_safe("<div class='date_column' >" + value + "</div>")

    render_created = render_isodate
    render_updated = render_isodate
    render_read_start = render_isodate
    render_read_end = render_isodate
    render_synced = render_isodate

    def render_userRating(self, value):
        if not value:
            return "-"
        if int(value) != value:
            # e.g. 4.5 -> '4+'
            value = int(value)
            return "%s+" % value
        return int(value)


class BooksTableFilter(django_filters.FilterSet):
    
    title = django_filters.CharFilter(label='title', lookup_expr='icontains')
    authors__name = django_filters.CharFilter(label='authors', lookup_expr='icontains')
    userRating_gt = django_filters.NumberFilter(label='Rating', field_name='userRating', lookup_expr='gte')
      ## TODO field width smaller for Rating
    
    class meta:
        model = books


class BooksTableFilterView(SingleTableMixin, FilterView):
    table_class = BooksTable
    model = books
    template_name = "books_table_filtered.html"
    filterset_class = BooksTableFilter
    
    def __init__(self, *args, **kwargs):
        super(BooksTableFilterView, self).__init__(*args, **kwargs)

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super(BooksTableFilterView, self).get_filterset_kwargs(filterset_class)
        # kwargs['attribute'] = 'width'
        return kwargs