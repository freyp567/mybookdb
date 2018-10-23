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

    def resolve_users(self, info):
        UserModel = get_user_model()
        return UserModel.objects.all()
    
    def resolve_all_authors(self, info):
        return authors.objects.all()
    
    def resolve_all_books(self, info):
        return books.objects.all()
    

schema = graphene.Schema(query=Query)
