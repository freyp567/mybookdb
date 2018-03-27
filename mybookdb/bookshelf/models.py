"""
django model for bookshelf app
"""
from django.db import models
from django.contrib.auth.models import User


class books(models.Model):
    """ books 
    adapted as closely as possible from MyBookDroid table book - 
    to achieve sqllite binary compatible
    """

    _id = models.AutoField(primary_key=True)
    isbn10 = models.TextField(blank=True)
    isbn10 = models.TextField(blank=True)
    title = models.TextField(blank=True)
    binding = models.TextField(blank=True)
    description = models.TextField(blank=True)
    numberOfPages = models.TextField(blank=True)
    publisher = models.TextField(blank=True)
    publicationDate = models.IntegerField()
    reviewsFetchedDate = models.IntegerField()
    offersFetchedDate = models.IntegerField()

    #author = models.ForeignKey(user)
    #authorBooks # authorId, bookId
    #tags = models.ManyToManyField(Tag, related_name="books", blank=True)
    # bookGroup (bookId, groupId)

    grRating = models.FloatField()
    grRatingsCount = models.IntegerField()
    subject = models.TextField(blank=True)
    created = models.IntegerField()
    stateId = models.IntegerField()
    userRating = models.IntegerField()
    authors = models.TextField(blank=True)
    lentToName = models.TextField(blank=True)
    lentToUri = models.TextField(blank=True)
    familyName = models.TextField(blank=True)
    thumbnailSmall = models.TextField(blank=True)
    thumbnailLarge = models.TextField(blank=True)
    amazonBookId = models.IntegerField()
    grBookId = models.IntegerField()
    googleBookId = models.IntegerField()

    def __str__(self):
        #return f"{self.title} | {self.author}"
        return f"{self.title}"


class comments(models.Model):
    """ comments on books """
    _id = models.AutoField(primary_key=True)
    #bookId  ... REFERENCES books ON DELETE SET NULL ON UPDATE SET NULL,
    bookId = models.ForeignKey(books, 
        related_name='bookId',
        null = True,
        on_delete=models.SET_NULL, 
        #on_update=models.SET_NULL. # not supported by Django ORM?
        )
    text = models.TextField()
    bookTitle = models.TextField()
    dateCreated = models.IntegerField()


class authors(models.Model):
    """ authors """
    _id = models.AutoField(primary_key=True)
    name = models.TextField()
    lowerCaseName = models.TextField()
    familyName = models.TextField()


class googleBooks(models.Model):
    """ googlebooks infos """
    _id = models.AutoField(primary_key=True)
    bookId = models.IntegerField()
    identifier = models.TextField()
    subtitle = models.TextField()
    subject = models.TextField()
    publisher = models.TextField()
    description = models.TextField()
    format = models.TextField()
    googleLink = models.TextField()


class grBooks(models.Model):
    """ goodreads books infos """
    _id = models.AutoField(primary_key=True)
    bookId = models.IntegerField()
    grId = models.TextField()
    grAvgRating = models.FloatField()
    grRatingsCount = models.IntegerField()
    grRatingsSum = models.IntegerField()
    grRatingDistOne = models.IntegerField()
    grRatingDistTwo = models.IntegerField()
    grRatingDistThree = models.IntegerField()
    grRatingDistFour = models.IntegerField()
    grRatingDistFive = models.IntegerField()
    grLinkDetail = models.TextField()


class groups(models.Model):
    """ book categories """
    _id = models.AutoField(primary_key=True)
    name = models.TextField()


class reviews(models.Model):
    """ reviews """
    _id = models.AutoField(primary_key=True)
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
    _id = models.AutoField(primary_key=True)
    bookId = models.IntegerField()
    favorite = models.IntegerField(default=0)
    haveRead = models.IntegerField(default=0)
    readingNow = models.IntegerField(default=0)
    iOwn = models.IntegerField(default=0)
    toBuy = models.IntegerField(default=0)
    toRead = models.IntegerField(default=0)
