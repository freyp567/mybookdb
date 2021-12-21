#from django.shortcuts import render
from timeline.models import timelineevent

from timeline.forms import BookEventCreateForm, BookEventDeleteForm

from django.views import generic
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt  # csrf_protect

import logging
LOGGER = logging.getLogger(name='mybookdb.timeline.views')


def get_book(book_id):
    # decouple timeline view from bookshelf model
    from bookshelf.models import books
    book_obj = books.objects.get(pk=book_id)
    return book_obj
    
def get_timeline_event(book_id, event_id):    
    from timeline.models import timelineevent
    event_obj = timelineevent.objects.get(id=event_id)
    # assert event_obj.xxx == book_id  # book is a ForwardManyToOneDescriptor
    return event_obj

class BookEventListView(generic.ListView):
    """
    List dates / location events for current book
    uses template timeline/timelineevent_list.html
    """
    model = timelineevent
    paginate_by = 25
    ordering = ['-is_bc', 'date']

    # @method_decorator(csrf_exempt)
    def get(self, request, *args, **kwargs):
        self.book_id = kwargs['pk']
        self.book_obj = get_book(self.book_id)
        return super(BookEventListView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        """ restrict to current book"""
        qs = super(BookEventListView, self).get_queryset()
        qs = qs.filter(book=self.book_id)
        return qs
    
    def get_context_data(self, *args, **kwargs):
        """Get the context for this view."""
        context = super(BookEventListView, self).get_context_data(*args, **kwargs)
        context["book"] = self.book_obj
        context["book_id"] = self.book_id
        context["book_title"] = self.book_obj.book_title
        context["book_search"] = '"%s" rezension' % self.book_obj.title  # TODO add author name
        context['is_paginated'] = False        
        return context
            

    
class BookEventCreateView(generic.CreateView):
    """ add new date / location """

    permission_required = 'bookshelf.can_create'
    model = timelineevent
    form_class = BookEventCreateForm
 
    def get(self, request, *args, **kwargs):
        self.book_id = kwargs['pk']
        self.book_obj = get_book(self.book_id)
        return super(BookEventCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.book_id = kwargs['pk']
        self.book_obj = get_book(self.book_id)
        return super().post(request, *args, **kwargs)
    
    def get_context_data(self, *args, **kwargs):
        """Get the context for this view."""
        context = super(BookEventCreateView, self).get_context_data(*args, **kwargs)
        context["book_title"] = self.book_obj.book_title
        context["book_search"] = '"%s" rezension' % self.book_obj.title  # TODO add author name
        context['is_paginated'] = False       
        if kwargs.get('form') and kwargs['form'].errors:
            context['messages'] = ['validation failed',]
        return context

    def get_form_kwargs(self):
        kwargs = super(BookEventCreateView, self).get_form_kwargs()
        initial = kwargs["initial"]
        initial["book_id"] = self.book_id
        return kwargs

    def form_valid(self, form):
        form.instance.book = self.book_obj
        return super(BookEventCreateView, self).form_valid(form)
    
    def form_invalid(self, form):
        # form.instance.book = self.book_obj
        LOGGER.error("failed to validate form: %s", form.errors)
        return super(BookEventCreateView, self).form_invalid(form)
    
    def get_success_url(self): 
        success_url = reverse('timeline:show-timeline', args=(self.book_id,))
        return success_url
 
 
class BookEventDeleteView(generic.DeleteView):

    permission_required = 'bookshelf.can_create'
    model = timelineevent
    # form_class = BookEventDeleteForm

    #def get(self, request, *args, **kwargs):
    #    book_id = kwargs['book_id']
    #    self.book_obj = get_book(book_id)
    #    # self.event_obj = get_timeline_event(book_id, event_id) # see BaseDetailView.get
    #    return super(BookEventDeleteView, self).get(request, *args, **kwargs)

    #def post(self, request, *args, **kwargs):  # TODO use delete
    #    book_id = kwargs['pk']
    #    self.book_obj = get_book(book_id)
    #    return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """ update context dict, add book object """
        context = {}
        context['object'] = self.object
        context['timelineevent'] = self.object
        context['book'] = self.object.book
        return context

    def get_success_url(self): 
        event_obj = self.object
        book_id = event_obj.book_id        
        success_url = reverse('timeline:show-timeline', args=(book_id,))
        return success_url


class TimelineView(generic.ListView):
    """ show timeline """
    template_name = "timeline/timeline.html"
    model = timelineevent
    paginate_by = 25
    ordering = ['is_bc', '-date']

    def get(self, request, *args, **kwargs):
        return super(TimelineView, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        """Get the context for this view."""
        context = super(TimelineView, self).get_context_data(*args, **kwargs)
        context['is_paginated'] = True
        return context
    
    def get_book_info(self, *args, **kwargs):
        return "TODO book_info"
