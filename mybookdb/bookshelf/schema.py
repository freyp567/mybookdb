# GraphQL schema for mybookdb 
# see https://github.com/graphql-python/graphene-django

# from graphene import relay, ObjectType
import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from django.contrib.auth import get_user_model
from .models import authors, books

class User(DjangoObjectType):
    class Meta:
        model = get_user_model()

class AuthorNode(DjangoObjectType):
    class Meta:
        model = authors
        filter_fields = ['id', 'name']
        interfaces = (graphene.relay.Node,)

class BookNode(DjangoObjectType):
    class Meta:
        model = books
        filter_fields = {
            'id': ['exact'], 
            'title': ['exact', 'icontains', 'istartswith'],
        }
        interfaces = (graphene.relay.Node, )

class Query(object):
    users = graphene.List(User)
    authors = graphene.relay.node.Field(AuthorNode)
    all_authors = DjangoFilterConnectionField(AuthorNode)
    books = graphene.relay.node.Field(BookNode)
    all_books = DjangoFilterConnectionField(BookNode)


# see mybookdb/schema.py for toplevel schema instance
