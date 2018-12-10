import json
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

from bookmarks.models import author_links, book_links

def get_bookmarks_stats(request):
    author_links_count = author_links.object.count()
    book_links_count = book_links.object.count()
    stats = {
        'author_links': author_links_count,
        'book_links': book_links_count,
    }
    return JsonResponse(stats)
