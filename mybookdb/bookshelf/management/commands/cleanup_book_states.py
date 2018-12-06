"""
cleanup book - states relationship (onetoone)
to ensure that book id and state id match in correspondance
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from bookshelf.models import books, states

import os
import io
import copy
from datetime import datetime, date
import sqlite3


class Command(BaseCommand):
    help = 'Cleanup book states relationship'

    def add_arguments(self, parser):
        pass #parser.add_argument('xxx', type=str) # nargs='+', 
        
    def handle(self, *args, **options):
        # dbpath = options['xxx']
        self.stdout.write(f"cleanup book states relationship")
        
        ok = 0
        book_id_max = 0
        for book_obj in books.objects.all():
            if book_obj.id > book_id_max:
                book_id_max = book_obj.id
            if not hasattr(book_obj, 'states'):
                self.stdout.write("ignore book without state: %s '%s'" % (book_obj.id, book_obj.title))
            else:
                state_obj = book_obj.states
                if state_obj.id != book_obj.id:
                    self.stdout.write("state id mismatch for book: %s '%s' state-id=%s" % 
                                      (book_obj.id, book_obj.title, state_obj.id))
                else:
                    ok += 1
        
        state_id_max = 0
        for state_obj in states.objects.all():
            if state_obj.id > state_id_max:
                state_id_max = state_obj.id
            if not hasattr(state_obj, 'book'):
                self.stdout.write("detected dangling state id=" +state_obj.id)
                state_obj.delete()
                state_obj.save()

        print("number of books verified to be ok: %s" % ok)
        print("autoincrement books: %s  states: %s" % (book_id_max, state_id_max))
