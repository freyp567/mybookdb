from django import template
from bookmarks.models import linksites

register = template.Library()


@register.simple_tag
def bookmarks_count():
    author_links_count = author_links.object.count()
    book_links_count = book_links.object.count()    
    return '<div style="color:red">Bookmarks: Books=%s Authors=%s</div>' %\
           (author_links_count, book_links_count)


@register.inclusion_tag('show_bookmarks.html')
def show_bookmarks(obj):
    if getattr(obj, 'author_links', None):
        links = obj.author_links.all()
        obj_type ='authors'
    elif getattr(obj, 'book_links', None):
        links = obj.book_links.all()
        obj_type = 'books'
    else:
        links = []
        obj_type = 'unknown'
    
    link_infos = []
    for link in links:
        link_info = {'link': link}
        try:
            site_obj = linksites.objects.get(pk=link.link_site)
            link_info['site_name'] = site_obj.name
        except:
            link_info['site_name'] = "?"
        link_infos.append(link_info)
    result_info = {
        'obj_id': obj.id,
        'obj_type': obj_type,
        'links': links, 
        'link_infos': link_infos,
    }
    return result_info


@register.inclusion_tag('edit_bookmarks.html')
def edit_bookmarks(obj):
    if obj:
        links = obj.author_links.all()
    else:
        links = []
    return {'obj': obj, 'links': links}
