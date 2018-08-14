from django.contrib import admin
from .models import books, authors, comments

# Register your models here.
admin.site.register(books)
admin.site.register(authors)
