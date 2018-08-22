from django import forms
#from django_select2.fields import HeavySelect2TagField

#from .models import books, authors


class AuthorsMultipleTagField(forms.ModelMultipleChoiceField):
    """  """
    # adapted from https://github.com/applegrew/django-select2/issues/297
    _choices = tuple()

    def __init__(self, *args, **kwargs):
        """ initialize field """
        #self.authors = kwargs.pop('authors')
        super(AuthorsMultipleTagField, self).__init__(*args, **kwargs)

    def create_new_value(self, value):
        """ Create a new entry """
        value = value.strip()
        authors = value.split()

        # Is this an already existing 1flow user that wants to be created???
        if authors[-1].startswith(u'@'):
            raise ValueError(u'bad value %s' % value)

        if value not in (None, u''):
            self.authors.update(add_to_set__authors=value)
            # self.authors.safe_reload()
