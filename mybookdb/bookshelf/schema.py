# GraphQL schema for mybookdb 
# see https://github.com/graphql-python/graphene-django

from graphene_django import DjangoObjectType
import graphene
from django.contrib.auth import get_user_model

class User(DjangoObjectType):
    class Meta:
        model = get_user_model()

class Query(graphene.ObjectType):
    users = graphene.List(User)

    def resolve_users(self, info):
        UserModel = get_user_model()
        return UserModel.objects.all()

schema = graphene.Schema(query=Query)
