"""
import from books.db backup

usage:
  python manage.py import_booksdb 2018-11-25.backup
  
TODO fix umlaute troubles, 
e.g. book 179 causing (unicode error) 'utf-8' codec can't decode byte 0xe4 in position 156: invalid continuation byte
book 336   'Im Land der wei?en Wolke: Roman'

TODO check for author uniqueness

ATTN current implementation assumes that author names are unique (or made unique)
hopefully case same author name matches several authors will be very seldom
and can be solved by 'discriminating' the author names with a suffix

"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from bookshelf.models import books, authors, comments, grBooks, googleBooks, groups, states

import os
import io
import copy
from datetime import datetime, date
import sqlite3


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('dbpath', type=str) # nargs='+', 

        
    def load_table(self, table_name, objType):
        self.stdout.write(f"loading data for table {table_name} ...")
        rowcount = updated = 0
        rows = self._c.execute(f"SELECT * FROM {table_name}")
        col_names = [ col_info[0] for col_info in self._c.description ]
        for row in rows:
            rowcount += 1
            data = {}
            id = None
            book_id = None
            book_obj = None
            for pos, value in enumerate(row):
                col_name = col_names[pos]
                if col_name == '_id':
                    data['id'] = id = value
                    
                elif col_name == "bookId":
                    book_id = value
                    try:
                        book_obj = books.objects.get(id=book_id)
                    except ObjectDoesNotExist:
                        book_obj = None
                    else:
                        data['book'] = book_obj
                    
                elif col_name in ('created','dateCreated',):
                    # MyBookDroid stores dates as time_t values, need to convert for Django ORM
                    if value:
                        data[col_name] = datetime.fromtimestamp(value//1000).date()
                    else:
                        data[col_name] = None
                    
                elif col_name == 'description':
                    if table_name in ('googleBooks',):
                        data["description"] = value
                    else:
                        data["orig_description"] = value 
                    
                else:
                    data[col_name] = value

            if table_name in ('comments',):
                if book_obj is None:
                    objs = books.objects.filter(title = data['bookTitle'])
                    if objs:
                        assert len(objs) == 1
                        book_obj = objs[0]
                        data['book'] = book_obj
                    else:
                        self.stderr.write(f"missing book {book_id} - {data['bookTitle']!r}")
                        continue # do not add if book it relates to does no longer exist
                    
                elif book_obj.title != data['bookTitle']: # title mismatch?
                    if book_obj.title in data['bookTitle']:
                        # e.g. 'Die letzte Legion. Roman' vs 'Die letzte Legion. Roman.'
                        pass
                    else:
                        #assert book_obj.title == data['bookTitle'], "title mismatch"
                        # pass similarity, e.g. 'Im Land der wei?en Wolke: Roman' vs 'Im Land der weissen Wolke: Roman'
                        self.stdout.write(f"title mismatch for book {book_obj.id}:\n  {book_obj.title!r}\n  {data['bookTitle']!r}\n.")
                        
            elif table_name in ('grBooks','states',) and book_obj is None:
                # skip if missing book it relates to
                continue
            
            #obj = objType.objects.get(pk=id) # raises DoesNotExist if not found, so avoid
            obj = objType.objects.filter(id=id)
            if obj:
                # item does already exist
                assert len(obj) == 1
                obj = obj[0]
                diff = {}
                for key, value in data.items():
                    if getattr(obj, key) != value:
                        diff[key] = (getattr(obj, key), value) 
                if diff:
                    keys = ", ".join(diff.keys())
                    self.stdout.write(f"update changes to {table_name} {id} keys={keys}")
                    # update changed fields
                    for key, value in diff.items():
                        assert key not in ('id',), "not allowed to update %s" % key 
                        value = value[1]  # new value
                        setattr(obj, key, value)
                    obj.updated = datetime.now(tz=timezone.utc)
                    try:
                        obj.save()
                    except BaseException as err:
                        # for debugging, to set breakpoint
                        raise
                    updated += 1
            else:
                obj = objType(**data)
                obj.updated = datetime.now(tz=timezone.utc)
                obj.save()
                updated += 1
                
        self.stdout.write(f"{table_name}: total {updated} rows updated (of total {rowcount})")
        return updated
        

    def update_book_authors(self, book_obj, authors_set, authors_new):
        authors_set_ids = set([ a.id for a in authors_set])
        authors_new_ids = set([ a.id for a in authors_new])
        if authors_set_ids == authors_new_ids:  # A ^ B, symmetric difference
            return # same, unchanged

        id = book_obj.id
        updated = 0
        delta_new = authors_new_ids - authors_set_ids
        for author_id in delta_new:
            author = authors.objects.get(pk=author_id)
            self.stderr.write(f"book {id} with author added: {author.name} id={author.id}")
            author.updated = datetime.now(tz=timezone.utc)
            author.save()
            book_obj.authors.add(author_id)
            book_obj.save()
            updated += 1
                
        delta_dropped = authors_set_ids - authors_new_ids 
        for author_id in delta_dropped:
            author = authors.objects.get(pk=author_id)
            self.stderr.write(f"book {id} with author removed: {author.name} id={author.id}")
            author.updated = datetime.now(tz=timezone.utc)
            author.save()
            book_obj.authors.remove(author.id)
            book_obj.save()
            updated += 1
            
        assert updated > 0, "failed to update book authors"

    def load_books(self):
        self.stdout.write(f"loading data for table books ...")
        rowcount = updated = 0
        book_count = self._c.execute(f"SELECT count(*) FROM books").fetchone()[0]
        book_rows = self._c.execute(f"SELECT * FROM books") # sqlite3_get_table?
        col_names = [ col_info[0] for col_info in self._c.description ]
        for row in book_rows:
            rowcount += 1
            #self.stdout.write(".", ending=rowcount % 100 == 0 and "\n" or "")
            self.stdout.flush()
            id = row[col_names.index('_id')]
            book_title = row[col_names.index('title')]
            book_authors = set()
            data = { 'id': id }
            for pos, value in enumerate(row):
                col_name = col_names[pos]
                if col_name == '_id':
                    continue
                    
                if col_name == 'description':
                    col_name = 'orig_description'
                    
                if col_name == 'authors':
                    author_unkn = []
                    if value is None:
                        self.stderr.write(f"book without author: {id} {book_title!r}")
                        continue 
                    
                    value =  [value]  # normalize!
                    while value:
                        author_name = value.pop().strip()
                        obj_author = authors.objects.filter(name=author_name)
                        if not obj_author and ',' in author_name:
                            authors_list = [ a.strip() for a in author_name.split(',')]
                            value.extend(authors_list)
                            continue
                        
                        # name, familyName, lowerCaseName
                        if not obj_author:
                            author_unkn.append(author_name) 
                            self.stdout.write(f"lookup author {author_name!r} unknown, auto-create for book {id} {book_title!r}")
                            obj_authors = authors.objects.create(name=author_name)
                            obj_authors.save()
                        else:
                            assert len(obj_author) == 1, "trouble with author %s" % author_name
                            book_authors.add(obj_author[0])
                            
                elif col_name in ('reviewsFetchedDate', 'offersFetchedDate', 'created', 'publicationDate'):
                    # MyBookDroid stores dates as time_t values, need to convert for Django ORM
                    if value:
                        data[col_name] = datetime.fromtimestamp(value//1000).date()
                    else:
                        data[col_name] = None
                    
                elif col_name == 'familyName': 
                    # eliminate redundancy, see ForeignKey set for col authors
                    pass 
                
                elif col_name in ('grBookId', 'googleBookId', 'stateId'):
                    # avoid TypeError: Direct assignment to the reverse side of a related set is prohibited. Use grBookId.set() instead.
                    pass
                
                else:
                    data[col_name] = value
                    
            book_obj = books.objects.filter(id=id)
            if book_obj:
                # item does already exist
                book_obj = book_obj[0]
                self.stdout.write(f"existing book {id}: {data['title']!r}")
                diff = {}
                for key, value in data.items():
                    if getattr(book_obj, key) != value:
                        diff[key] = (getattr(book_obj, key), value) 
                        
                # detect changes in book - authors relationship (many-to-many)
                book_authors_set = list(book_obj.authors.all())
                self.update_book_authors(book_obj, book_authors_set, book_authors)
                        
                diff2 = copy.copy(diff)  # save
                # discard fields not relevant for update
                for key in ('reviewsFetchedDate',):
                    if key in diff:
                        del diff[key]
                if diff: # handle other differences
                    keys = ", ".join(diff2.keys())
                    self.stdout.write(f"detected changes for book {id} keys={keys}")
                    # update changed fields, e.g. title
                    for key, value in diff2.items():
                        assert not key in ('id',) # disallow update
                        old_value, new_value = value
                        if key in ('reviewsFechedDate',):
                            value = new_value  #.isoformat()
                        else:
                            value = new_value
                        setattr(book_obj, key, value)
                    book_obj.updated = datetime.now(tz=timezone.utc)  #.isoformat()[:10]
                    book_obj.save()
                else:
                    pass # no changes
                    
            else:
                self.stdout.write(f"new book {id}: {data['title']!r}")
                book_obj = books(**data)
                book_obj.save()
                for author in book_authors:  
                    book_obj.authors.add(author.id)
                book_obj.save()
                
                updated += 1
                
        self.stdout.write("")
        self.stdout.write(f"books: total {updated} rows updated (of total {rowcount})")
        return updated
        

    def handle(self, *args, **options):
        dbpath = options['dbpath']
        self.stdout.write(f"importing books.db from {dbpath}")
        assert os.path.isfile(dbpath), "missing dbpath"
        
        # https://docs.python.org/3/library/sqlite3.html
        conn = sqlite3.connect(dbpath)
        self._c = conn.cursor()
        
        self.load_table('authors', authors)
        self.load_table('groups', groups)
            
        self.load_books()

        self.load_table('states', states)
        # self.load_table('bookGroup', bookGroup) # TODO 

        self.load_table('googleBooks', googleBooks)
        self.load_table('grBooks', grBooks)        
        self.load_table('comments', comments)
        
        self.stdout.write(self.style.SUCCESS(f"import books.db succeeded"))
        