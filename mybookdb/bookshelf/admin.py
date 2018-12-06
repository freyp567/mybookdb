from django.contrib import admin
from .models import books, authors, comments, reviews, states

# Register your models here.
admin.site.register(books)
admin.site.register(authors)
admin.site.register(reviews)
admin.site.register(states)
