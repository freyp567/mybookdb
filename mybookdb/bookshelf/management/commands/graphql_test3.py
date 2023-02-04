"""
integration test #2 for graphql 
replaces graphql_test2.py after switching to use relay 

/graphql?variables=null&operationName=null&query=...

for interantive GraphQL console:
/graphiql  

{ allAuthors {  edges { node { id name }}} }
{ allAuthors { pageInfo { startCursor endCursor } }}


{ allBooks {  edges { node { id title isbn10 isbn13 }}} }

{ allBooks {  edges { node { id title isbn10 isbn13 
  authors { edges { node { id name } }}
}}} }


{ allAuthors(id:"QXV0aG9yTm9kZTo4NQ==") {  edges { node { id name }}} }


query { allBooks(title_Icontains:"Die Insel unter dem Meer") {edges{node{
  title
  authors {edges{node{
    name
  }}}
}}}}


"""
# see https://github.com/graphql-python/graphene-django
# and http://docs.graphene-python.org/projects/django/en/latest/tutorial-relay/#testing-our-graphql-schema
# and https://blog.apollographql.com/explaining-graphql-connections-c48b7c3d6976

from django.core.management.base import BaseCommand  # , CommandError

from mybookdb.schema import schema
import sys
import pprint


class Command(BaseCommand):
    help = 'simple GraphQL integration test'
    
    def verify_result(self, result):
        """ verify and show result from GraphQL query run 
        result is a graphql.execution.base.ExecutionResult object
        """
        if result.invalid or result.errors:
            # e.g. [ GraphQLError('Cannot query field "name" on type "User". Did you mean "username"?',)]
            self.stderr.write("graphql query failed")
            self.pprint(result.errors)
            assert result.errors, "result invalid but no errors?"
            sys.exit(1)  # integration test failed
        else:
            self.pprint(result.to_dict())
        
    def all_authors(self):
        self.stdout.write("list all authors")
        query = '''
            query
            { allAuthors {  edges { node { id name }}} }
        '''
        result = schema.execute(query)
        self.stdout.write("got result for query: %s" % query)
        self.verify_result(result)
        self.stdout.write("\n")
        
    def all_books(self):
        self.stdout.write("list all books")
        query = '''
            query
            { allBooks {  edges { node { id title isbn10 isbn13 }}} }
        '''
        result = schema.execute(query)
        self.stdout.write("got result for query: %s" % query)
        self.verify_result(result)
        self.stdout.write("\n")
        
    def books_authors(self):
        self.stdout.write("list books and authors")
        query = '''
{ allBooks {  edges { node { id title isbn10 isbn13 
  authors { edges { node { id name } }}
}}} }
        '''
        result = schema.execute(query)
        self.stdout.write("got result for query: %s" % query)
        self.verify_result(result)
        self.stdout.write("\n")
        
    def book_by_title(self, title):
        self.stdout.write("show book for given title '%s'" % title)
        query = '''
{allBooks(title:"%s") 
  { edges { node { id title 
  authors { edges { node { id name }} }
}}}}
        ''' % title
        result = schema.execute(query)
        self.stdout.write("got result for query: %s" % query)
        self.verify_result(result)
        self.stdout.write("\n")
        
    def pprint(self, *args, **kwargs):
        pp = pprint.PrettyPrinter(indent=2, stream=sys.stdout)
        # note: passing stream=self.stdout ignores indent
        pp.pprint(*args, **kwargs)
        
    def handle(self, *args, **options):
        # xyz = options.get('xyz')
        self.stdout.write(f"test graphene integration")
        self.all_authors()
        self.all_books()
        # self.books_authors() # fails - django orm .select_related and many-to-many-relations?
        # see https://stackoverflow.com/questions/1387044/django-select-related-with-manytomanyfield
        self.book_by_title("Die Insel unter dem Meer: Roman")
        self.stdout.write("finished.\n")
        