from django.urls import reverse_lazy
from django_select2.forms import HeavySelect2TagWidget

class AuthorsTagWidget(HeavySelect2TagWidget):
    data_url = reverse_lazy('authors_book')

    def render(self, *args, **kwargs):
        # replace `choices` as we only want selected options to be in the list
        #values = args[1]
        #tag_dikt = {force_text(tag.pk): tag.name for tag in Tag.objects.filter(pk__in=values)}
        #kwargs['choices'] = [(force_text(k), tag_dikt[force_text(k)]) for k in values]
        return super(AuthorsTagWidget, self).render(*args, **kwargs)

    def set_to_cache(self):
        pass  # we don't need to cache this

    def value_from_datadict(self, data, files, name):
        return super(AuthorsTagWidget, self).value_from_datadict(data, files, name)
