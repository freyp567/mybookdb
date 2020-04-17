"""
django model for bookshelf app
"""
from django.db import models
from django.contrib.auth.models import User

from django.urls import reverse 
import datetime


class authors(models.Model):
    """ authors """
    name = models.TextField()
    lowerCaseName = models.TextField()
    familyName = models.TextField()
    updated = models.DateField(null=True)
    short_bio = models.TextField(null=True)
    
    def __str__(self):
        return f"{self.familyName}, {self.name}"

    class Meta:
        indexes = [
            models.Index(fields=['name'], name='author_name'),
        ]
        
    @property
    def latest_book(self):
        b = self.books_set.all().order_by('-created')
        return b and b[0].book_title or None
        
    @property
    def last_book_update(self):
        updated = None
        b = self.books_set.all().order_by('-updated')[:1]
        if b and b[0].updated:
            updated = b[0].updated 
        return updated
        
    @property
    def book_count(self):
        b = self.books_set.all()
        return len(b)
    
    @property
    def books_read(self):
        b = self.books_set.filter(states__haveRead = True)
        return len(b)
        
    @property
    def book_rating_avg(self):
        book_count = 0
        rating = 0
        for b in self.books_set.all():
            if b.userRating:
                book_count += 1
                rating += b.userRating
        if rating:
            # average rating er book
            rating /= book_count
            return round(rating, 1)
        else:
            # no books read
            return None
        

class books(models.Model):
    """ books 
    adapted as closely as possible from MyBookDroid table book - 
    to achieve sqllite binary compatible
    """

    isbn10 = models.TextField(null=True, max_length=10)
    isbn13 = models.TextField(null=True, max_length=13)
    title = models.TextField(blank=False, max_length=255)
    unified_title = models.TextField(null=True)
      # unified title (may different from title synced with mybookdroid that is 'title')
    binding = models.CharField(max_length=80, null=True)
    orig_description = models.TextField(null=True, blank=True)  
      # original descriptin from MyBookDroid app
    new_description = models.TextField(null=True, blank=True)
    numberOfPages = models.CharField(max_length=10, blank=True, null=True)
    publisher = models.TextField(blank=True, null=True)
    publicationDate = models.DateField(null=True)
    reviewsFetchedDate = models.DateField(null=True)
    offersFetchedDate = models.DateField(null=True)

    #tags = models.ManyToManyField(Tag, related_name="books", blank=True)
    # bookGroup (bookId, groupId)
    
    grRating = models.FloatField(null=True)
    grRatingsCount = models.IntegerField(null=True) # TODO move to grBooks
    subject = models.TextField(null=True, blank=True)
    created = models.DateField()
    updated = models.DateField(null=True)
    userRating = models.IntegerField(null = True)
    
    authors = models.ManyToManyField(authors)
    
    lentToName = models.CharField(max_length=120, null=True)
    lentToUri = models.TextField(blank=True, null=True)
    thumbnailSmall = models.TextField(blank=True, null=True)
    thumbnailLarge = models.TextField(blank=True, null=True)
    amazonBookId = models.IntegerField(null=True)
    
    @property
    def book_title(self):
        if self.unified_title:
            return self.unified_title
        else:
            return self.title
        
    @property
    def description(self):
        """ computed from new_/orig_description """
        if self.new_description:
            return self.new_description
        return self.orig_description

    def has_states(self):
        return hasattr(self, 'states')
    
    @property
    def state_info(self):
        return self.states.state_info

    @property
    def onleihe_status(self):
        if not getattr(self, 'onleihebooks', None):
            return ''
        status = self.onleihebooks.status
        if status == 'confirmed':
            return 'onleihe'
        if status == 'notfound':
            return 'NOT onleihe'
        return 'onleihe:%s' % status

    class Meta:
        permissions = (
            ("can_create", "Create book"),
            ("can_edit", "Edit book"),
            ("can_delete", "Delete book"),
        )   
        
    def get_absolute_url(self):
        """
        Returns the url to access a particular book instance.
        """
        url = reverse('bookshelf:book-detail', args=[str(self.id)])
        return url


    def __str__(self):
        #return f"{self.title} | {self.author}"
        return f"{self.book_title}"


class comments(models.Model):
    """ comments on books """
    #bookId  ... REFERENCES books ON DELETE SET NULL ON UPDATE SET NULL,
    book = models.ForeignKey(books, 
        null = True,
        on_delete=models.SET_NULL, 
        #on_update=models.SET_NULL. # not supported by Django ORM?
        )
    text = models.TextField()
    bookTitle = models.TextField()
    dateCreatedInt = models.BigIntegerField(null=True)
    dateCreated = models.DateTimeField()
    
    class Meta:
        ordering = ['-dateCreated']
        
    @property
    def datetime_created(self):
        """ dateCreated is only date (with tz shift) """
        if self.dateCreatedInt:
            created = datetime.datetime.utcfromtimestamp(self.dateCreatedInt/1000)
            return created.strftime("%Y-%m-%dT%H:%M")
        elif self.dateCreated:
            return self.dateCreated.strftime("%Y-%m-%dT%H:%M")
        else:            
            return '(NA)'

    @property
    def clean_text(self):
        comment_date = self.dateCreated.date().isoformat()
        comment_text = self.text
        if comment_date in comment_text:
            comment_text = comment_text.replace(comment_date, '')
        return comment_text
    
    def __str__(self):
        return "comment %s book=%s '%s'" % (self.id, self.book.id, self.book.book_title)


class onleiheBooks(models.Model):
    """ onleihe infos """
    book = models.OneToOneField(books, 
        # related_name="onleiheBookId",
        on_delete=models.CASCADE,
        )
    onleiheId = models.TextField(null=True)
    status = models.TextField(null=False)  # 'confirmed', ...
    bookCoverURL = models.TextField(null=True)
    author = models.TextField(null=True)
    translator = models.TextField(null=True)
    year = models.IntegerField(null=True)
    isbn = models.TextField(null=True, max_length=13)
    #metaKeywords = models.TextField(null=True) # Array
    #category = # Array or many to many # TODO fix later, for searching
    category = models.TextField(null=True) # string, separated by '/'
    #keywords = # Array or many to many # TODO fix later, for searching
    keywords = models.TextField(null=True) # string, comma separated
    publisher = models.TextField(null=True)
    #language = models.TextField(null=True)
    format = models.TextField(null=True)
    pages = models.IntegerField(null=True)
    # filesize', 'Dateigröße'],
    # copies', 'Exemplare'],
    # available', 'Verfügbar'],
    # reservations', 'Vormerker'],
    # available_after', 'Voraussichtlich verfügbar ab'],
    allow_copy = models.NullBooleanField(null=True)
    book_description = models.TextField(null=True)
    updated = models.DateField(null=True)
    comment = models.TextField(null=True, blank=True)
    
    def __str__(self):
        value = []
        if self.onleiheId:
            value.append(self.onleiheId)
        if not self.status in ('confirmed',):
            value.append(self.status)
        if not value:
            value.append('?')
        if self.updated:
            value.append(' updated %s' % self.updated)
        return "onleihe(%s)" % (",".join(value))
    
    
class googleBooks(models.Model):
    """ googlebooks infos """
    book = models.OneToOneField(books, 
        related_name="googleBookId",
        on_delete=models.CASCADE,
        )
    identifier = models.TextField()
    subtitle = models.TextField(null=True)
    subject = models.TextField(null=True)
    publisher = models.TextField(null=True)
    description = models.TextField(null=True)
    format = models.TextField(null=True)
    googleLink = models.TextField(null=True)


class grBooks(models.Model):
    """ goodreads books infos """
    book = models.OneToOneField(books, 
        related_name="grBookId",
        on_delete=models.CASCADE,
        )
    grId = models.TextField(null=True)
    grAvgRating = models.FloatField(null=True)
    grRatingsCount = models.IntegerField(null=True)
    grRatingsSum = models.IntegerField(null=True)
    grRatingDistOne = models.IntegerField(null=True)
    grRatingDistTwo = models.IntegerField(null=True)
    grRatingDistThree = models.IntegerField(null=True)
    grRatingDistFour = models.IntegerField(null=True)
    grRatingDistFive = models.IntegerField(null=True)
    grLinkDetail = models.TextField(null=True)


class groups(models.Model):
    """ book categories """
    name = models.TextField()


class reviews(models.Model):
    """ reviews """
    book = models.OneToOneField(books, 
        null=True,
        on_delete=models.CASCADE,
        )
    grReviewId = models.TextField()
    dateCreated = models.BigIntegerField()
    #dateCreated = models.DateTimeField()
    userName = models.TextField()
    userUrl = models.TextField()
    url = models.TextField()
    body = models.TextField()
    fullBody = models.TextField()
    rating = models.IntegerField()
    votes = models.IntegerField()
    spoiler = models.TextField()


class states(models.Model):
    """ book status read/unread/... """
    book = models.OneToOneField(books, 
        null=True,
        on_delete=models.CASCADE,
        )
    favorite = models.BooleanField(default=False)
    haveRead = models.BooleanField(default=False)
    readingNow = models.BooleanField(default=False)
    iOwn = models.BooleanField(default=False)
    toBuy = models.BooleanField(default=False)
    toRead = models.BooleanField(default=False)
    
    def __init__(self, *args, **kwargs):
        return super(states, self).__init__(*args, **kwargs)
        
    def __str__(self):
        state_value = []
        for key in ('favorite', 'readingNow', 'haveRead', 'toRead', 'toBuy', 'iOwn'):
            value = getattr(self, key)
            if value == True:
                state_value.append(key)
            elif value is None:
                state_value.append("(%s?)" % key)
        return 'states(%s)' % (' '.join(state_value),)

    @property
    def book_title(self):
        return self.books.book_title
        
    @property
    def state_info(self):
        state_info = []
        if self.favorite:
            state_info.append('++')
        if self.iOwn:
            state_info.append('-')
        if self.haveRead:
            state_info.append('read')
        if self.readingNow:
            state_info.append('reading')
        if self.toRead:
            state_info.append('to read')
        if self.toBuy:
            state_info.append('wish')
        return ' '.join(state_info)

