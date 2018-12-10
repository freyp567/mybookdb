from django.db import models
from bookshelf.models import books, authors


class linktargets(models.Model):
    # valid link targets
    name = models.TextField(null=False)
    description = models.TextField(null=True)
    base_url = models.TextField(null=False)
 

class links(models.Model):
    # link (URL, ...) to external content
    link_name = models.TextField(null=False)  # short name describing link
    link_target = models.TextField(null=False) # values from linktargets
    link_uri = models.TextField(null=False)
    link_state = models.TextField(null=False)  # 'ok', 'stale', 'broken'
    created = models.DateField(null=False)
    updated = models.DateField(null=False)
    verified = models.DateField(null=True)

    class Meta:
        abstract = True    
    
class book_links(links):
    book = models.ForeignKey(
        'bookshelf.books', 
        related_name='book_links',
        on_delete=models.CASCADE,
    )
    
class author_links(links):
    author = models.ForeignKey(
        'bookshelf.authors', 
        related_name='author_links',
        on_delete=models.CASCADE,
    )
    
