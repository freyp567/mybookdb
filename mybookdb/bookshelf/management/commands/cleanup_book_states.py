"""
cleanup book - states relationship (onetoone)
to ensure that book id and state id match in correspondance
what is important for the sync between mybookdb and mybookdroid
"""

from django.core.management.base import BaseCommand
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
        parser.add_argument('--fixup', action='store_true')
        parser.add_argument('--purge', action='store_true')
        
    def handle(self, *args, **options):
        self.stdout.write(f"cleaning up book states ...")
        fixup = options.get('fixup')
        purge = options.get('purge')
        
        ok = not_ok = fixups = 0
        book_id_max = 0
        for book_obj in books.objects.all():
            if book_obj.id > book_id_max:
                book_id_max = book_obj.id
            if not hasattr(book_obj, 'states'):
                state_obj_list = states.objects.filter(pk=book_obj.id)
                if fixup:
                    if len(state_obj_list) == 1:
                        state_obj = state_obj_list[0]
                        self.stderr.write("assign lost state: book=%s state=%s" % (book_obj, state_obj))
                        state_obj.book = book_obj
                        state_obj.save()
                        fixups += 1
                    else:
                        assert not state_obj_list, "found state object not assigned to book %s" % book_obj.id
                        self.stdout.write("fixup book without state: %s '%s'" % (book_obj.id, book_obj.title))
                        state_obj = states(pk=book_obj.id)
                        state_obj.book = book_obj
                        state_obj.save()
                        fixups += 1
                    assert hasattr(book_obj, 'states'), "book without state"  # still missing?
                elif state_obj_list:
                    self.stderr.write("found state object not assigned to book %s: %s" %
                                      (book_obj.id, [obj.id for obj in state_obj_list]))
                    not_ok += 1
                else:
                    self.stdout.write("found book without state: %s '%s'" % (book_obj.id, book_obj.title))
                    not_ok += 1
            else:
                if book_obj.states.id != book_obj.id:
                    state_obj = book_obj.states
                    self.stdout.write("state id mismatch for book: %s state: %s" % 
                                      (book_obj, state_obj))
                    book_obj2 = books.objects.filter(pk=state_obj.id)
                    state_obj_list = states.objects.filter(pk=book_obj.id)
                    if fixup:
                        if book_obj2:
                            assert len(book_obj2) == 1, "multiple books assigned to same state?"
                            book_obj2 = book_obj2[0]
                            self.stderr.write("unlink state %s assigned to book %s from states list for book %s" %
                                              (state_obj.id, book_obj2.id, book_obj.id))
                            if state_obj_list:
                                # already have state, re-assign
                                assert len(state_obj_list) ==1, "found multiple state objects assigned to book %s" % book_obj.id
                                state_obj2 = state_obj_list[0]
                                self.stderr.write("reassigned state %s to book %s %s" % (state_obj2.id, book_obj.id, book_obj.title))
                                state_obj.book = None
                                state_obj.save()
                                state_obj2.book = book_obj
                                state_obj2.save()
                                fixups += 1
                            else:
                                # lost state, create new one
                                new_state_obj = states(pk=book_obj.id)
                                new_state_obj.book = book_obj
                                for key in state_obj.fields:
                                    value = getattr(state_object, key, None)
                                    if value is not None:
                                        setattr(new_state_obj, key, value)                                       
                                new_state_obj.save()
                                self.stderr.write("create new state %s for book %s %s" %
                                                  (new_state_obj.id, book_obj.id, book_obj.title))
                                fixups += 1
                        else:
                            assert len(states.objects.filter(pk=book_obj.id)) == 0, "wrong state assigned"
                            self.stderr.write("unlink bad state from book=%s: state=%s" % (book_obj, state_obj))
                            state_obj.book = None
                            state_obj.save()
                            new_state_obj = states(pk=book_obj.id)
                            new_state_obj.book = book_obj
                            self.stderr.write("link to new state %s for book %s %s" %
                                              (new_state_obj.id, book_obj.id, book_obj.title))
                            new_state_obj.save()     
                            book_obj.save()
                            not_ok += 1
                    else:
                        not_ok += 1
                        
                else:
                    ok += 1
        
        state_id_max = 0
        for state_obj in states.objects.all():
            if state_obj.id > state_id_max:
                state_id_max = state_obj.id
            if not hasattr(state_obj, 'book'):
                if purge:
                    self.stdout.write("purged dangling state id=" +state_obj.id)
                    state_obj.delete()
                    state_obj.save()
                    fixups += 1
                else:
                    self.stdout.write("detected dangling state id=" +state_obj.id)
                    not_ok += 1

        print("books verified to be ok: %s" % ok)
        if not_ok:
            print("books with issues: %s" % not_ok)
        if fixups:
            print("book issues corrected: %s" % fixups)
            
        print("autoincrement books: %s  states: %s" % (book_id_max, state_id_max))

