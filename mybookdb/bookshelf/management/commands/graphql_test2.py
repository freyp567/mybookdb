"""
integration test for graphql 
/graphql?variables=null&operationName=null&query=...

{ allAuthors { id name }}

"""
# see https://github.com/graphql-python/graphene-django
# and http://docs.graphene-python.org/projects/django/en/latest/tutorial-plain/#hello-graphql-schema-and-object-types

from django.core.management.base import BaseCommand  # , CommandError

from bookshelf.schema import schema
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
        
    def allAuthors(self):
        self.stdout.write("list all authors")
        query = '''
            query
            { allAuthors { id name }}
        '''
        result = schema.execute(query)
        self.stdout.write("got result for query: %s" % query)
        self.verify_result(result)
        
    def allBooks(self):
        self.stdout.write("list all authors")
        query = '''
            query
            { allBooks { id title }}
        '''
        result = schema.execute(query)
        self.stdout.write("got result for query: %s" % query)
        self.verify_result(result)
        
    def pprint(self, *args, **kwargs):
        pp = pprint.PrettyPrinter(indent=2, stream=sys.stdout)
        # note: passing stream=self.stdout ignores indent
        pp.pprint(*args, **kwargs)
        
    def handle(self, *args, **options):
        # xyz = options.get('xyz')
        self.stdout.write(f"test graphene integration")
        # self.allAuthors()
        self.allBooks()
        self.stdout.write("finished.\n")
        