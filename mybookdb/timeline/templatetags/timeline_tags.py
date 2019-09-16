"""
template tags for timeline app
"""

from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from bookshelf.models import books

register = template.Library()


@register.simple_tag
def timeline_book_link(event):
    book_obj = books.objects.get(pk=event.book_id)
    book_title = book_obj.title
    if len(book_title) > 50:
        book_title = book_title[:48] +'..'
    book_url = reverse('bookshelf:book-detail', args=(event.book_id,))
    html = '<a href="%s">%s</a>' % (book_url, book_title)
    return mark_safe(html)
