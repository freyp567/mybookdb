# GraphQL schema for mybookdb 
# see https://github.com/graphql-python/graphene-django

from graphene_django import DjangoObjectType
import graphene
from django.contrib.auth import get_user_model
from .models import authors, books

class User(DjangoObjectType):
    class Meta:
        model = get_user_model()

class Author(DjangoObjectType):
    class Meta:
        model = authors

class Book(DjangoObjectType):
    class Meta:
        model = books

class Query(graphene.ObjectType):
    users = graphene.List(User)
    all_authors = graphene.List(Author)
    all_books = graphene.List(Book)
    # book_authors = graphene.List(Book)
    book = graphene.Field(Book,
                          id=graphene.Int(),
                          title=graphene.String()
                          )

    def resolve_users(self, info):
        UserModel = get_user_model()
        return UserModel.objects.all()
    
    def resolve_all_authors(self, info):
        return authors.objects.all()
    
    def resolve_all_books(self, info):
        return books.objects.all()
    
    #def resolve_book_authors(self, info, **kwargs):
        #return books.objects.select_related('authors').all()
        ## fails with django.core.exceptions.FieldError: 
        ## Invalid field name(s) given in select_related: 'author'.
        ## Choices are: googleBookId, grBookId, reviews, states

    def resolve_book(self, info, **kwargs):
        id = kwargs.get('id')
        title = kwargs.get('title')
        if id is not None:
            return books.objects.get(pk=id)
        if title is not None:
            return books.objects.get(title=title)
        return None
    
    
schema = graphene.Schema(query=Query)
