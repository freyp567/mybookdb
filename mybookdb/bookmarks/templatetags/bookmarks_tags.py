from django import template

register = template.Library()


@register.simple_tag
def bookmarks_count():
    author_links_count = author_links.object.count()
    book_links_count = book_links.object.count()    
    return '<div style="color:red">Bookmarks: Books=%s Authors=%s</div>' %\
           (author_links_count, book_links_count)


@register.inclusion_tag('show_bookmarks.html')
def show_bookmarks(obj):
    links = obj.author_links.all()
    return {'links': links}


@register.inclusion_tag('edit_bookmarks.html')
def edit_bookmarks(obj):
    links = obj.author_links.all()
    return {'links': links}
