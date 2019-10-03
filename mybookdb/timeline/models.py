"""
timeline add-on for mybookdb
record timeline events
"""
from django.db import models
from partial_date import PartialDateField
from bookshelf.models import books

class timelineevent(models.Model):
    # timeline event with optional location and comment
    book = models.ForeignKey(books, on_delete=models.CASCADE)
    date = PartialDateField()
    is_bc = models.BooleanField(default=False)
    # TODO evaluate datautil.date.FlexiDate, but need a widget for input 
    location = models.TextField(null=True)
    comment = models.TextField(null=True)
