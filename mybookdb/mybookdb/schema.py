import graphene

import bookshelf.schema


class Query(bookshelf.schema.Query, graphene.ObjectType):
    # inherit from app-specific GraphQL queries
    pass 

schema = graphene.Schema(query=Query)
