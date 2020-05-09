"""
set field updated for authors, books, ...
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from bookshelf.models import books, authors

import os
import io
import copy
from datetime import datetime, date
import sqlite3


class Command(BaseCommand):
    help = 'Set Updated'

    def add_arguments(self, parser):
        pass #parser.add_argument('xxx', type=str) # nargs='+', 
        
    def handle(self, *args, **options):
        # dbpath = options['xxx']
        self.stdout.write(f"set field .updated for authors")
        updated_authors = 0
        for author_obj in authors.objects.all():
            if author_obj.updated is None:
                # author_obj.updated = author_obj.created
                b = author_obj.books_set.all().order_by('created')[:1]
                if b:
                    author_obj.updated = b[0].created
                    author_obj.save()
                    updated_authors += 1
        
        self.stdout.write(f"set field .updated for books")        
        updated_books = 0
        for book_obj in books.objects.all():
            if book_obj.updated is None:
                book_obj.updated = book_obj.created
                book_obj.save()
                updated_books += 1
                
        print("number of updates authors=%s books=%s" % (updated_authors, updated_books))
        return
