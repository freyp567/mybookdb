"""
import from books.db backup

usage:
  python manage.py import_booksdb 20180121.backup
  
"""
from django.core.management.base import BaseCommand, CommandError
from bookshelf.models import books, authors, comments, grBooks, googleBooks, groups

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
        for row in self._c.execute(f"SELECT * FROM {table_name}"):
            rowcount += 1
            col_names = [ col_info[0] for col_info in self._c.description ]
            data = {}
            id = None
            for pos, value in enumerate(row):
                col_name = col_names[pos]
                if col_name == '_id':
                    data['id'] = id = value
                    
                elif col_name in ('created',):
                    # MyBookDroid stores dates as time_t values, need to convert for Django ORM
                    if value:
                        data[col_name] = datetime.fromtimestamp(value//1000).date()
                    else:
                        data[col_name] = None
                    
                else:
                    data[col_name] = value
                    
            #obj = objType.objects.get(pk=id) # raises DoesNotExist if not found, avoid
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
                    
            else:
                obj = objType(**data)
                # 
                obj.save()
                updated += 1
        self.stdout.write(f"{table_name}: total {updated} rows updated (of total {rowcount})")
        return updated
        

    def load_books(self):
        self.stdout.write(f"loading data for table books ...")
        rowcount = updated = 0
        book_authors = set()
        for row in self._c.execute(f"SELECT * FROM books"):
            rowcount += 1
            col_names = [ col_info[0] for col_info in self._c.description ]
            data = {}
            id = None
            for pos, value in enumerate(row):
                col_name = col_names[pos]
                if col_name == '_id':
                    data['id'] = id = value
                    
                elif col_name == 'authors':
                    for author_name in value.split(','):
                        author_name = author_name.strip()
                        obj_author = authors.objects.filter(name = author_name)
                        # name, familyName, lowerCaseName
                        if not obj_author:
                            self.stdout.write(f"lookup author {author_name!r} failed for book {id} ({value})")
                        elif len(obj_author) != 1:
                            test = obj_author[0] # name not unique??
                            assert len(obj_author) == 1, f"author name not unique: {author_name}"
                        else:
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
                
                elif col_name in ('grBookId', 'googleBookId',):
                    # avoid TypeError: Direct assignment to the reverse side of a related set is prohibited. Use grBookId.set() instead.
                    continue
                
                else:
                    data[col_name] = value
                    
            obj = books.objects.filter(id=id)
            if obj:
                # item does already exist
                assert len(obj) == 1
                obj = obj[0]
                diff = {}
                for key, value in data.items():
                    if key == 'authors':
                        pass # TODO detect changes in book_authors
                    elif getattr(obj, key) != value:
                        diff[key] = (getattr(obj, key), value) 
                        
                if diff:
                    keys = ", ".join(diff.keys())
                    self.stdout.write(f"detected mismatch for {table_name} {id} keys={keys}")
                    # TODO update selected fields
                    
            else:
                obj = books(**data)
                obj.save()
                #obj.set(book_authors)
                for author in book_authors:  
                    obj.authors.add(author)
                obj.save()
                
                updated += 1
                
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
        self.load_table('googleBooks', googleBooks)
        self.load_table('grBooks', grBooks)        
        self.load_table('comments', comments)

        self.stdout.write(self.style.SUCCESS(f"import books.db succeeded"))
        