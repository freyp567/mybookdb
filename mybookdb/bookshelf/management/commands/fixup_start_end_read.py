"""
fix fields read_start and read_end by guessing values from mybookdroid comments

"""

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from bookshelf.models import books, comments


class Command(BaseCommand):
    help = 'Sync with export.csv created by Book Catalogue'

    def __init__(self, stdout=None, stderr=None, no_color=False):
        self._conflicts_books = []
        self.differs = {}
        super().__init__(stdout, stderr, no_color)

    def determine_read_start_end(self, book_obj):
        read_start = getattr(book_obj, 'read_start', None)
        read_end = getattr(book_obj, 'read_end', None)
        if read_start is not None:
            # know already, no need to guess
            age = read_start - book_obj.created
            if age > timedelta(days=30):
                diff = age.days
                self.stdout.write(f"read_start and created differ for {book_obj}, days={diff}")
                diff = diff  #TODO examine
            if read_end is None:
                read_end = read_end  # guess, fix?
                self.stdout.write(f"have read_start but no read_end for {book_obj}, set it to {read_end}")
            return read_start, read_end
        if read_end is not None:
            # know end reading, but not start
            read_start = read_end -timedelta(days=28)
            self.stdout.write(f"have read_end but no read_start for {book_obj}, set it to {read_start}")
            return read_start, read_end            
        
        read_start = None
        for comment_obj in comments.objects.filter(book=book_obj).order_by('dateCreated'):
            if not read_start:
                read_start = comment_obj.dateCreated
                read_end = read_start
            if comment_obj.dateCreated > read_end:
                since = comment_obj.dateCreated - read_start
                if since > timedelta(weeks=12):   # ignore if > 12 weeks from read_start
                    break
                read_end = comment_obj.dateCreated
            if 'zuende' in comment_obj.text or 'gelesen' in comment_obj.text:
                break
        if read_start:
            read_start = read_start.date()
        else:
            read_start = None
        if read_end:
            read_end = read_end.date()
            assert read_end >= read_start
        else:
            read_end = None
        if read_start:
            self.stdout.write(f"guess read_start for {book_obj}: {read_start}")            
            if read_start and read_start == read_end:
                # missing info on read_end, assume 28 days
                read_end = read_start + timedelta(days=28)
                self.stdout.write(f"compute read_end for {book_obj}: {read_end}")
            else:
                self.stdout.write(f"guess read_end for {book_obj}: {read_end}")
        else:
            self.stdout.write(f"unable to guess read_start for {book_obj}")            
        
        return read_start, read_end
        
        
    def handle(self, *args, **options):
        self.stdout.write("fixup_start_end_read ...")
        updated = 0
        for book_obj in books.objects.all():
            book_info = f"{book_obj.book_title!r} id= {book_obj.id}"
            if not hasattr(book_obj, "states"):
                self.stdout.write(f"missing state for {book_info}")
                continue
            if book_obj.states.toRead:
                continue
            if book_obj.states.obsolete:
                continue
            if book_obj.states.iOwn:
                pass
            elif not book_obj.states.haveRead:
                continue
            read_start, read_end = self.determine_read_start_end(book_obj)
            if not read_start:
                self.stdout.write(f"failed to guess read_start for {book_info} state={book_obj.states}")
                read_start = book_obj.created
                read_end = datetime.combine(read_start, datetime.min.time())
                read_end = read_end + timedelta(days=28)
                read_end = read_end.date()
            update = False
            if not book_obj.read_start:
                book_obj.read_start = read_start
                self.stdout.write(f"update read_start={read_start} for {book_info}")
                update = True
            if not book_obj.read_end:
                book_obj.read_end = read_end
                self.stdout.write(f"update read_end={read_end} for {book_info}")
                update = True
            if update:
                book_obj.save()
                updated += 1
        self.stdout.write(f"finished, updated {updated} books.")
        return
