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

TODO readjust authors if added both in mybookdb and mybookdroid, avoid duplication
TODO handle duplicated books from Merkliste and added after checkout
TODO books marked obsolete, delete after sync when not in mybookdroid - else log error

"""
"""
usage notes:

after initial create of database / before adding own books in mybookdb make sure to adjust
the autoincrement values of all tables, to avoid collisions when resyncing mybookdroid backup
with database later on; e.g.

python manage.py dbshell
mysql> ALTER TABLE books AUTO_INCREMENT = 5000;
# Error: near "AUTO_INCREMENT": syntax error
...

ALTER TABLE `table` AUTO_INCREMENT = number;

sqlite> select max(id) from bookshelf_books;
679

sqlite> select name,seq from sqlite_sequence where name = 'bookshelf_books';
bookshelf_books|679

sqlite> update sqlite_sequence set seq = 5000 where name = 'bookshelf_books';

update sqlite_sequence set seq = 5000 where name = 'bookshelf_authors';
update sqlite_sequence set seq = 50000 where name = 'bookshelf_comments';
update sqlite_sequence set seq = 5000 where name = 'bookshelf_googlebooks';
update sqlite_sequence set seq = 5000 where name = 'bookshelf_grbooks';
update sqlite_sequence set seq = 20000 where name = 'bookshelf_groups';
update sqlite_sequence set seq = 5000 where name = 'bookshelf_reviews';
update sqlite_sequence set seq = 5000 where name = 'bookshelf_states';
update sqlite_sequence set seq = 500000 where name = 'bookshelf_books_authors';

sqlite> select name,seq from sqlite_sequence;
django_migrations|28
django_admin_log|3
django_content_type|15
auth_permission|48
auth_user|2
bookshelf_groups|20000
bookshelf_books_authors|500000
bookshelf_googlebooks|5000
bookshelf_grbooks|5000
bookshelf_reviews|5000
bookshelf_comments|50000
auth_user_user_permissions|4
bookshelf_authors|5000
bookshelf_books|5000
bookshelf_states|5000
bookshelf_onleihebooks|24

"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from bookshelf.models import books, authors, comments, grBooks, googleBooks, groups, states
from bookmarks.models import author_links, book_links, linksites
from timeline.models import timelineevent


import os
import io
import copy
from datetime import datetime, date
import sqlite3


class Command(BaseCommand):
    help = 'Imports backup from mybookdroid app'

    def __init__(self, stdout=None, stderr=None, no_color=False):
        self._conflicts_books = []
        self._books_nostate = []
        self._books_ignorechange =[]
        self._conflicts_authors = []
        super().__init__(stdout, stderr, no_color)
        
    def add_arguments(self, parser):
        parser.add_argument('dbpath', type=str) 
        parser.add_argument('--only', default='')

    def same_value_table(self, table_name, key, curr_value, new_value):
        """ similar to same_value, but for tables associated to book objects (states, ...) """
        if curr_value == new_value:
            return True
        
        if isinstance(curr_value, datetime) and not isinstance(new_value, datetime):
            # avoid rounding errors caused by comparing datetime (tz ware) and date (naive) values
            new_value = datetime.combine(new_value, datetime.min.time())
            new_value = new_value.astimezone(timezone.utc)                        
            
        if curr_value == new_value:
            return True
        
        if table_name == 'states':
            if key in ('toRead', 'toBuy', 'haveRead', 'readingNow') and curr_value == True:
                # keep value if state flag is set, dont reset
                return None
            return False
        
        return False
        
        
    def load_authors(self):
        self.stdout.write(f"loading data for authors ...")
        rows = self._c.execute(f"SELECT * FROM authors")
        col_names = [ col_info[0] for col_info in self._c.description ]
        # '_id', 'name', 'lowerCaseName', 'familyName'
        rowcount = updated = 0
        for row in rows:
            rowcount += 1
            data = {}
            id = None
            for pos, value in enumerate(row):
                col_name = col_names[pos]
                if col_name == '_id':
                    data['id'] = id = value
                    
                else:
                    data[col_name] = value

            
            obj = authors.objects.filter(id=id)
            if obj:
                # author does already exist
                assert len(obj) == 1
                # never update authors created (and synced) by mybookdb
                continue
            
            # check if authors exists with same name - if created in mybookdb directly
            obj = authors.objects.filter(name=data['name'])
            if len(obj) != 0:
                assert len(obj) == 1  # author name not unique ??
                obj = obj[0]
                
                # books referencing this author?? 
                assigned = books.objects.filter(authors__name=data['name'])

                new_obj = authors(**data)
                new_obj.updated = datetime.now(tz=timezone.utc)
                new_obj.save()
                updated += 1
                
                # trahsfer author_links from obj to new_obj
                for link in author_links.objects.filter(author=obj):
                    link.author = new_obj
                    link.save()
                
                for book_obj in assigned:
                    # shift references to this author
                    book_obj.authors.add(new_obj)
                    book_obj.authors.remove(obj)
                    book_obj.save()
                obj.delete()
                continue
            
            # new author, create
            obj = authors(**data)
            obj.updated = datetime.now(tz=timezone.utc)
            obj.save()
            updated += 1
                
        self.stdout.write(f"authors: total {updated} rows updated (of total {rowcount})")
        return updated

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
                    
                elif book_obj.title != data['bookTitle']: # verify comment for this book
                    if book_obj.unified_title == data['bookTitle']:
                        self.stdout.write(f"title mismatch but match on unified title, book {book_obj}")
                    elif book_obj.title in data['bookTitle']:
                        # e.g. 'Die letzte Legion. Roman' vs 'Die letzte Legion. Roman.'
                        self.stdout.write(f"title mismatch but match for substring, book {book_obj}")
                    else:
                        #assert book_obj.title == data['bookTitle'], "title mismatch"
                        # pass similarity, e.g. 'Im Land der wei?en Wolke: Roman' vs 'Im Land der weissen Wolke: Roman'
                        self.stdout.write(f"title mismatch for book {book_obj.id}:\n  {book_obj.title!r}\n  {data['bookTitle']!r}\n.")
                        # this can usually be ignored, it happens if title is edited in mybookdroid (what is not updated in comments)
                        
            elif table_name in ('grBooks','states',) and book_obj is None:
                # skip if missing book it relates to
                continue
            
            if table_name == 'states':
                flags_set = [ key for key,value in data.items() if value != 0 and key not in ('id','book',)]
                if not flags_set:
                    # make sure that at least 'toRead' is set
                    self.stdout.write("foce toRead as no status flags set for %s" % book_obj)
                    data['toRead'] = 1
               
            if table_name == 'grBooks':
                data = data  # TODO normalize to avoid excessive updates

            # test if already synced
            obj = objType.objects.filter(id=id)
            if obj:
                # test if update required
                assert len(obj) == 1
                obj = obj[0]
                diff = {}
                for key, value in data.items():
                    obj_value = getattr(obj, key)
                    is_same = self.same_value_table(table_name, key, obj_value, value)
                    if is_same is None:
                        # ignore certain changes if target value is set
                        self._books_ignorechange.append(f"change {table_name} key={key} ignored -- book {book_id} {book_obj.title}")
                    elif is_same is not True:  # book_obj, key, value, obj_value
                        diff[key] = (getattr(obj, key), value) 
                        
                if diff:
                    keys = ", ".join(diff.keys())
                    self.stdout.write(f"update changes to {table_name} {id} keys={keys} for book {book_id} {book_obj.title}")
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

    def has_author(self, curr_author, new_author):
        """ mybookdb has both author and translator, want only first """
        for author in curr_author:
            if author in new_author:
                return True
        return False
        

    def update_book_authors(self, book_obj, authors_set, authors_new):
        authors_set_ids = set([ a.id for a in authors_set])
        authors_new_ids = set([ a.id for a in authors_new])
        if authors_set_ids == authors_new_ids:  # A ^ B, symmetric difference
            return # same, unchanged

        if self.has_author(authors_set, authors_new):
            return # already have
            
        id = book_obj.id
        updated = 0
        delta_new = authors_new_ids - authors_set_ids
        for author_id in delta_new:
            author = authors.objects.get(pk=author_id)
            self.stderr.write(f"book {id} '{book_obj.title}' with author added: {author.name} id={author.id}")
            author.updated = datetime.now(tz=timezone.utc)
            book_obj.authors.add(author_id)
            book_obj.save()
            author.save()
            updated += 1
        
        delta_dropped = authors_set_ids - authors_new_ids 
        if len(authors_new_ids) == 0:
            # do not remove authors if there is none left
            self.stderr.write(f"book {id} '{book_obj.title}' author(s) not removed: {authors_set_ids}")            
            self._conflicts_authors.append("%s not removed for %s '%s'" % (authors_set_ids, book_obj.id, book_obj.title))
            updated += 1
        else:
            for author_id in delta_dropped:
                author = authors.objects.get(pk=author_id)
                self.stderr.write(f"book {id} '{book_obj.title}' with author removed: {author.name} id={author.id}")
                author.updated = datetime.now(tz=timezone.utc)
                book_obj.authors.remove(author)
                book_obj.save()
                author.save()
                updated += 1
                
        assert updated > 0, f"failed to update authors for book {book_obj}"
        return

    def same_value(self, key, curr_value, new_value):
        """ compare current and new value for equality """
        if curr_value == new_value:
            return True
        
        if key in ('reviewsFetchedDate',):
            # not relevant for update, ignore 
            return True
        
        if not curr_value and not new_value:
            return True  # ignore pseudo change None vs ''
        
        if key == 'title':
            curr_value = curr_value.strip()
            new_value =new_value.strip()
        
        if key =='orig_description':
            curr_value = curr_value.replace('\r\n', '\n').strip()
            new_value = new_value.replace('\r\n', '\n').strip()
            
        if key in ('userRating',) and curr_value:
            # never update if already set
            return True
        
        if key == 'isbn13':
            if not new_value:
                # never reset
                return True
            if new_value and len(new_value) != 13:
                # mybookdroid sets isbn13 with isbn10 value by mistake, ignore #xxx TODO verify
                return True
        
        if key =='isbn10': #xxx TODO obsolete, drop - or convert to isbn13
            if not new_value:
                # never reset
                return True
        
        if key in ('subject',):
            if curr_value and not new_value:
                # never reset
                return True
            
        if key in ('publisher',):
            # always ignore updates
            return True
        
        if key == 'state':
            assert False ## requires more logic when to update
            return True
        
        return curr_value == new_value
        

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
                        elif len(obj_author) == 1:
                            book_authors.add(obj_author[0])
                        else:
                            self.stdout.write(f"duplicate author name:{author_name!r}")
                            self._conflicts_authors.append("%s duplicated (%s)" % (author_name, ', '.join([str(a.id) for a in obj_author])))
                            #for author_obj in obj_author:
                            #    book_authors.add(author_obj)
                                
                            
                elif col_name in ('reviewsFetchedDate', 'offersFetchedDate', 'created', 'publicationDate'):
                    # MyBookDroid stores dates as time_t values, need to convert for Django ORM
                    if value:
                        data[col_name] = datetime.fromtimestamp(value//1000).date()
                    else:
                        data[col_name] = None
                    
                elif col_name == 'familyName': 
                    # redundant, ignore
                    pass
                
                elif col_name in ('grBookId', 'googleBookId', 'stateId'):
                    # avoid TypeError: Direct assignment to the reverse side of a related set is prohibited. Use grBookId.set() instead.
                    pass
                
                else:
                    data[col_name] = value
                    
            book_obj = books.objects.filter(id=id)
            if not book_obj:
                # book not yet synced between mybookdroid and mybookdb, but may be created there with different id
                # and hopefully identical title; lookup and handle
                # happens if we import books from wishlist (onleihe Merkzettel), then check it out later on and add to mybookdroid
                found_by_title = books.objects.exclude(states__obsolete=True).filter(title=book_title)
                if not found_by_title:
                    found_by_title = books.objects.exclude(states__obsolete=True).filter(unified_title=book_title)
                if found_by_title:
                    assert len(found_by_title) == 1, "title not unique"  # needs more examination, which book to pick 
                    book_obj2 = found_by_title[0]
                    self.stdout.write(f"book does already exist with different id: {id} != {book_obj2}")
                    # happens if created in mybookdb in parallel to adding it to mybookdroid (e.g. added from onleihe Merkzettel)
                    book_obj = self.create_book_obj(data, book_authors)
                    updated += 1
                    
                    # transfer links etc from book_obj2 to book_obj
                    self.transfer_book_links(book_obj2, book_obj)
                    
                    if not book_obj.new_description:
                        book_obj.new_description = book_obj2.description
                        book_obj.save()
                    
                    # transfer comments
                    for comment in comments.objects.filter(book=book_obj2):
                        comment.book = book_obj
                        comment.save()
                        
                    # transfer timeline events
                    for event in timelineevent.objects.filter(book=book_obj2):
                        event.book = book_obj
                        event.save()
                    
                    # and mark the excessive book object as beeing obsolete
                    book_obj2.states.obsolete = True
                    book_obj2.save()
                    self._conflicts_books.append(f"{book_obj2} replaced by {book_obj}")
                
            if book_obj:
                # item does already exist
                assert len(book_obj) == 1
                self.update_book_obj(book_obj[0], data, book_authors)
                continue
                    
            found_by_title = books.objects.exclude(states__obsolete=True).filter(title=book_title)  #TODO verify obsolete? see above
            assert not found_by_title
            #if found_by_title:
                #if not books.objects.filter(id=id):
                    #other_book = found_by_title[0]
                    ## extract book_links, if any
                    ## links = book_links.objects.find(id=other_book.id)
                    ## save title if edited 
                    #assert False # TODO ro be resolved, cause of duplicated books
                    ## e.g. from Merkzettel imported to mybookdb (756 Der Circle)
                    ## later on checked out in onleihe and added to mybookdroid - as new book
                    ## book with lower id has precedence, needs to be update with info from other book
                    ## for description, urls, ...
                    
                    ## diffing ?
                    #self.stdout.write(f"already in mybooksdb with different id than {id}: {data['title']!r}")
                    #data['new_description'] = other_book.description  # retain (edited) description
                    #self._conflicts_books.append("%s '%s'" % (id, book_title))
                #else:
                    #assert False, "duplicate in mybooksdb: {data['title']!r}"  # or id collision
                    
            book_obj = self.create_book_obj(data, book_authors)
            updated += 1
                
        self.stdout.write("")
        self.stdout.write(f"books: total {updated} rows updated (of total {rowcount})")
        return updated

    def transfer_book_links(self, from_book_obj, to_book_obj):
        for link in book_links.objects.filter(book=from_book_obj):
            link.book = to_book_obj
            link.save()
        return
        
    def create_book_obj(self, data, book_authors):
        self.stdout.write(f"new book {data['id']}: {data['title']!r}")
        book_obj = books(**data)
        book_obj.save()
        for author in book_authors:  
            book_obj.authors.add(author.id)
        book_obj.updated = datetime.now(tz=timezone.utc)
        book_obj.sync_mybookdroid = datetime.now(tz=timezone.utc)                
        book_obj.save()
        return book_obj
        
    def update_book_obj(self, book_obj, data, book_authors):
        # self.stdout.write(f"update book {id}: {data['title']!r}") # blather
        try:
            if book_obj.states.obsolete:
                self.stdout.write(f"skip update book marked obsolete: {book_obj}")
                self._conflicts_books.append(f"{book_obj} -- obsolete")
                return
        except states.DoesNotExist:
            # RelatedObjectDoesNotExist - rare cases missing States
            self.stdout.write(f"book without state: {book_obj}")
            self._books_nostate.append(f"{book_obj}")
        
        diff = {}
        for key, new_value in data.items():
            curr_value = getattr(book_obj, key)
            if not self.same_value(key, curr_value, new_value):
                diff[key] = (curr_value, new_value) 
                
        # detect changes in book - authors relationship (many-to-many)
        book_authors_set = list(book_obj.authors.all())
        self.update_book_authors(book_obj, book_authors_set, book_authors)
                
        if len(diff) > 0: # handle other differences
            keys = ", ".join(diff.keys())
            self.stdout.write(f"detected changes for book {id} '{book_obj.title}' fields={keys}")
            # update changed fields, e.g. title
            for key, value in diff.items():
                assert not key in ('id',) # disallow update
                old_value, new_value = value
                if key in ('reviewsFechedDate',):
                    value = new_value  #.isoformat()
                else:
                    value = new_value
                setattr(book_obj, key, value)
            book_obj.updated = datetime.now(tz=timezone.utc)
            book_obj.sync_mybookdroid = datetime.now(tz=timezone.utc)
            book_obj.save()
        else:
            # no changes, but update last sync date
            book_obj.sync_mybookdroid = datetime.now(tz=timezone.utc)
            book_obj.save()
        return
        
    def output_sqllite(self, *args, **kwards):
        if args[0].startswith('SELECT '):
            return 
        # attempt to suppress verbose logging by sqllite, but in vain
        return

    def handle(self, *args, **options):
        dbpath = options['dbpath']
        self.stdout.write(f"importing books.db from {dbpath}")
        assert os.path.isfile(dbpath), "missing dbpath"
        
        # https://docs.python.org/3/library/sqlite3.html
        conn = sqlite3.connect(dbpath)  # TODO reduce verbosity
        conn.set_trace_callback(self.output_sqllite)
        self._c = conn.cursor()
        
        only = [tn.strip() for tn in options.get('only', '').split(',')]
        only = [tn for tn in only if tn]  # drop empty entries
        if not only or 'authors' in only:
            self.load_authors()

        if not only or 'groups' in only:
            self.load_table('groups', groups)
            
        if not only or 'books' in only:
            self.load_books()
    
        if not only or 'states' in only:
            self.load_table('states', states)
            
        if only and 'bookGroup' in only:  # not synced unless explicitly requested
            self.load_table('bookGroup', bookGroup)
    
        if not only or 'googleBooks' in only:
            self.load_table('googleBooks', googleBooks)
            
        if only and 'grBooks' in only:
            TODO = 1  # self.load_table('grBooks', grBooks)  # TODO diffing needs to be fixed
            
        if only and 'comments' in only:
            self.load_table('comments', comments)
        
        self.stdout.write(self.style.SUCCESS(f"import books.db succeeded"))

        if self._books_ignorechange:
            self.stderr.write("ignored changes:\n")
            self.stderr.write("%s\n" % "\n".join(self._books_ignorechange))
            self.stderr.write(".\n")            
            
        if self._books_nostate:
            self.stderr.write("books without state:\n")
            self.stderr.write("%s\n" % "\n".join(self._books_nostate))
            self.stderr.write(".\n")            
            
        if self._conflicts_books:
            self.stderr.write("conflicts for books:\n")
            self.stderr.write("%s\n" % "\n".join(self._conflicts_books))
            self.stderr.write(".\n")
            
        if self._conflicts_authors:
            self.stderr.write("conflicts for authors:\n")
            self.stderr.write("%s\n" % "\n".join(self._conflicts_authors))
            self.stderr.write(".\n")

        