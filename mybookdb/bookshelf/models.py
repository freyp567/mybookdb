"""
django model for bookshelf app
"""
from django.db import models
from django.contrib.auth.models import User

from django.urls import reverse 


class authors(models.Model):
    """ authors """
    name = models.TextField()
    lowerCaseName = models.TextField()
    familyName = models.TextField()
    updated = models.DateField(null=True)
    
    def __str__(self):
        return f"{self.familyName}, {self.name}"

    class Meta:
        indexes = [
            models.Index(fields=['name'], name='author_name'),
        ]
        
    @property
    def latest_book(self):
        b = self.books_set.all().order_by('-created')
        return b and b[0].title or None
        
    @property
    def book_count(self):
        b = self.books_set.all()
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
    def description(self):
        """ computed from new_/orig_description """
        if self.new_description:
            return self.new_description
        return self.orig_description

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
        url = reverse('book-detail', args=[str(self.id)])
        return url


    def __str__(self):
        #return f"{self.title} | {self.author}"
        return f"{self.title}"


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
    dateCreatedInt = models.IntegerField(null=True)
    dateCreated = models.DateTimeField()
    
    class Meta:
        ordering = ['-dateCreated']


class onleiheBooks(models.Model):
    """ onleihe infos """
    book = models.OneToOneField(books, 
        # related_name="onleiheBookId",
        on_delete=models.CASCADE,
        )
    onleiheId = models.TextField(null=False)
    status = models.TextField(null=False)  # 'confirmed', ...
    bookCoverURL = models.TextField(null=True)
    #translator
    year = models.IntegerField()
    isbn = models.TextField(null=False, max_length=13)
    #metaKeywords = models.TextField() # Array
    #keywords = # Array
    publisher = models.TextField()
    #language = models.TextField()
    format = models.TextField()
    pages = models.IntegerField()
    # filesize', 'Dateigr��e'],
    # copies', 'Exemplare'],
    # available', 'Verf�gbar'],
    # reservations', 'Vormerker'],
    # available_after', 'Voraussichtlich verf�gbar ab'],
    allow_copy = models.BooleanField()
    book_description = models.TextField()
    
    
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
    dateCreated = models.IntegerField()
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
