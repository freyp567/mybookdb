from django.contrib import admin

from .models import linksites, book_links, author_links

admin.site.register(linksites)
admin.site.register(book_links)
admin.site.register(author_links)
