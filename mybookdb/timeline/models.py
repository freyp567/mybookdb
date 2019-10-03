"""
timeline add-on for mybookdb
record timeline events
"""
from django.db import models
from partial_date import PartialDateField
from bookshelf.models import books

class bookevent(models.Model):  #TODO eliminate
    # a timeline event with optional location and comment
    #xxx old style, replaced by timelineevent
    book_id = models.IntegerField(validators=())
    #   # note: not defining foreign key relatonship to make it independant of the bookshelf app
    #   # as books are normaly never deleted, we dont care about data integrity
    date = PartialDateField()
    location = models.TextField(null=True)
    comment = models.TextField(null=True)

class timelineevent(models.Model):
    # timeline event with optional location and comment
    book = models.ForeignKey(books, on_delete=models.CASCADE)
    date = PartialDateField()
    location = models.TextField(null=True)
    comment = models.TextField(null=True)
