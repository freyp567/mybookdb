from django.db import models
from bookshelf.models import books, authors


class linksites(models.Model):
    # valid link sites
    id = models.AutoField(primary_key=True)
    name = models.TextField(null=False)
    description = models.TextField(null=True)
    base_url = models.TextField(null=False)
 
class linksites_url(models.Model):
    id = models.AutoField(primary_key=True)
    site = models.ForeignKey(
        'linksites',
        related_name='site',
        on_delete=models.CASCADE,
    )
    url = models.TextField(null=False)

class links(models.Model):
    # link (URL, ...) to external content
    id = models.AutoField(primary_key=True)
    link_name = models.TextField(null=False)  # short name describing link
    link_site = models.TextField(null=False) # values from linksites
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
    
    def __str__(self):
        return "book_links link=%s for book %s" % (self.link_name, self.book)
    
class author_links(links):
    author = models.ForeignKey(
        'bookshelf.authors', 
        related_name='author_links',
        on_delete=models.CASCADE,
    )
    
    def __str__(self):
        return "author_links link=%s for author %s" % (self.link_name, self.author)
