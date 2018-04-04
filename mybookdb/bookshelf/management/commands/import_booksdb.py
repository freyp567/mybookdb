"""
import from books.db backup

usage:
  python manage.py import_booksdb 20180121.backup
  
TODO fix umlaute troubles, 
e.g. book 179 causing (unicode error) 'utf-8' codec can't decode byte 0xe4 in position 156: invalid continuation byte
book 336   'Im Land der wei?en Wolke: Roman'
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from bookshelf.models import books, authors, comments, grBooks, googleBooks, groups, states

import os
import io
from datetime import datetime, date
import sqlite3


import wingdbstub


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
                    
                elif col_name in ('created',):
                    # MyBookDroid stores dates as time_t values, need to convert for Django ORM
                    if value:
                        data[col_name] = datetime.fromtimestamp(value//1000).date()
                    else:
                        data[col_name] = None
                    
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
                    self.stdout.write(f"detected mismatch for {table_name} {id} keys={keys}")
                    # TODO update selected fields
                    obj.updated = datetime.now(tz=timezone.utc)
                    
            else:
                obj = objType(**data)
                obj.updated = datetime.now(tz=timezone.utc)
                obj.save()
                updated += 1
                
        self.stdout.write(f"{table_name}: total {updated} rows updated (of total {rowcount})")
        return updated
        

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
                    
                if col_name == 'authors':
                    author_unkn = []
                    if value is None:
                        self.stderr.write(f"book without author: {id} {book_title!r}")
                        continue 
                    
                    for author_name in value.split(','):
                        author_name = author_name
                        obj_author = authors.objects.filter(name=author_name.strip())                        
                        # name, familyName, lowerCaseName
                        if not obj_author:
                            author_unkn.append(author_name) # e.g. bookdId 106 ' Susanne Goga- Klinkenberg'
                        elif len(obj_author) != 1:
                            test = obj_author[0] # name not unique??
                            assert len(obj_author) == 1, f"author name not unique: {author_name}"
                        else:
                            book_authors.add(obj_author[0])
                            
                    if author_unkn:
                        # e.g. 'Wilbur, Smith'
                        author_name = ','.join(author_unkn)
                        obj_author = authors.objects.filter(name=author_name.strip())                        
                        if obj_author:
                            assert len(obj_author) == 1
                            book_authors.add(obj_author[0])
                        else:
                            self.stdout.write("")
                            self.stdout.write(f"lookup author {author_name!r} failed for book {id} {book_title!r}")
                        
                            
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
                        
                book_authors_set = set([ a.name for a in book_obj.authors.all() ])
                book_authors_add = []
                for book_author in book_authors:
                    if book_author.name in book_authors_set:
                        book_authors_set.remove(book_author.name) # matched, ok
                    else:
                        book_obj.authors.add(book_author)
                        book_obj.save()
                        book_authors_add.append(book_author.name)
                        
                # removed authors
                for book_author_name in book_authors_set:
                    # author no longer assigned
                    book_author = [ a for a in book_obj.authors.all() if a.name == book_author_name ]
                    assert len(book_author) == 1
                    book_author = book_author[0]
                    self.stderr.write(f"book {id} with author removed: {book_author.name}")
                    book_obj.authors.remove(book_author)
                    book_obj.save()
                        
                    
                if diff: # handle other differences
                    keys = ", ".join(diff.keys())
                    self.stdout.write(f"detected mismatch for {table_name} {id} keys={keys}")
                    # TODO update selected fields
                    
            else:
                self.stdout.write(f"new book {id}: {data['title']!r}")
                book_obj = books(**data)
                book_obj.save()
                for author in book_authors:  
                    book_obj.authors.add(author)
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
        self.load_table('bookGroup', bookGroup) # TODO

        self.load_table('googleBooks', googleBooks)
        self.load_table('grBooks', grBooks)        
        self.load_table('comments', comments)
        
        self.stdout.write(self.style.SUCCESS(f"import books.db succeeded"))
        