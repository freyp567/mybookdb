from django.urls import reverse_lazy
from django_select2.forms import HeavySelect2TagWidget

class AuthorsTagWidget(HeavySelect2TagWidget):
    data_url = reverse_lazy('authors_book')

    #def render(self, *args, **kwargs):
    #    # replace `choices` as we only want selected options to be in the list
    #    #values = args[1]
    #    #tag_dikt = {force_text(tag.pk): tag.name for tag in Tag.objects.filter(pk__in=values)}
    #    #kwargs['choices'] = [(force_text(k), tag_dikt[force_text(k)]) for k in values]
    #    return super(AuthorsTagWidget, self).render(*args, **kwargs)

    def set_to_cache(self):
        pass  # we don't need to cache this
    
    #def optgroups(name, value, attrs)
    def optgroups(self, name, value, attrs):
        opts = super(AuthorsTagWidget, self).optgroups(name, value, attrs)
        return opts
    
    def label_from_instance(self, obj):
        # https://django-select2.readthedocs.io/en/latest/django_select2.html#django_select2.forms.ModelSelect2Mixin.label_from_instance
        # TODO fix label creation -- is not called
        # http://srcmvn.com/blog/2013/01/15/django-advanced-model-choice-field
        return obj.name

    def value_from_datadict(self, data, files, name):
        """ pass back value to model """
        #data[name]
        #'authors': ['56', '363', '364'],
        # Thomas Jeier, Rebecca Gable
        result = super(AuthorsTagWidget, self).value_from_datadict(data, files, name)
        return result
