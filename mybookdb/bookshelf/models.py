"""
django model for bookshelf app
"""
from django.db import models
from django.contrib.auth.models import User


class authors(models.Model):
    """ authors """
    name = models.TextField()
    lowerCaseName = models.TextField()
    familyName = models.TextField()
    
    def __str__(self):
        return f"{self.familyName}, {self.name}"


class books(models.Model):
    """ books 
    adapted as closely as possible from MyBookDroid table book - 
    to achieve sqllite binary compatible
    """

    isbn10 = models.TextField(null=True)
    isbn13 = models.TextField(null=True)
    title = models.TextField(blank=False)
    binding = models.CharField(max_length=80, null=True)
    description = models.TextField(null=True, blank=True)
    numberOfPages = models.CharField(max_length=10, blank=True, null=True)
    publisher = models.TextField(blank=True, null=True)
    publicationDate = models.DateField(null=True)
    reviewsFetchedDate = models.DateField(null=True)
    offersFetchedDate = models.DateField(null=True)

    #author = models.ForeignKey(user)
    #authorBooks # authorId, bookId
    #tags = models.ManyToManyField(Tag, related_name="books", blank=True)
    # bookGroup (bookId, groupId)

    grRating = models.FloatField(null=True)
    grRatingsCount = models.IntegerField(null=True) # TODO move to grBooks
    subject = models.TextField(null=True, blank=True)
    created = models.DateField()
    updated = models.DateField(null=True)
    stateId = models.IntegerField() # TODO OneToOne or OneToMany?
    userRating = models.IntegerField(null = True)
    #authors = models.TextField(blank=True)
    authors = models.ManyToManyField(authors,
    )
    lentToName = models.CharField(max_length=120, null=True)
    lentToUri = models.TextField(blank=True, null=True)
    #familyName = models.TextField(blank=True) # TODO redundant?
    thumbnailSmall = models.TextField(blank=True, null=True)
    thumbnailLarge = models.TextField(blank=True, null=True)
    amazonBookId = models.IntegerField(null=True)
    #grBookId = models.IntegerField()
    #googleBookId = models.IntegerField()

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
    dateCreated = models.IntegerField()


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
    bookId = models.IntegerField()
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
    bookId = models.IntegerField()
    favorite = models.IntegerField(default=0)
    haveRead = models.IntegerField(default=0)
    readingNow = models.IntegerField(default=0)
    iOwn = models.IntegerField(default=0)
    toBuy = models.IntegerField(default=0)
    toRead = models.IntegerField(default=0)
