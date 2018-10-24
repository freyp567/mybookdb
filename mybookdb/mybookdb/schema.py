import graphene

import bookshelf.schema

from graphene_django.debug import DjangoDebug

class Query(bookshelf.schema.Query, graphene.ObjectType):
    # inherit from app-specific GraphQL queries
    debug = graphene.Field(DjangoDebug, name='__debug')

schema = graphene.Schema(query=Query)
