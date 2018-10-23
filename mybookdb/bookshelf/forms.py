from datetime import datetime, date
from django.core.exceptions import ValidationError
from django.urls import reverse, reverse_lazy
from django import forms
from django.forms import widgets
from django.utils.translation import gettext as _
#from django_select2.forms import HeavySelect2TagWidget
# ModelSelect2TagWidget 

from bookshelf.models import books, authors
#from .fields import AuthorsMultipleTagField
from bookshelf.widgets import AuthorsTagWidget


class BookUpdateForm(forms.ModelForm):
    """
    update book information
    """
    title = forms.CharField(max_length=255)
    new_description = forms.CharField()
    orig_description = forms.CharField(disabled=True, label="Original description")
    isbn10 = forms.CharField(max_length=10, min_length=10)
    isbn13 = forms.CharField(max_length=13, min_length=13)
    
    authors = forms.ModelMultipleChoiceField(
        queryset=authors.objects.none(), 
    )
    
    subject = forms.CharField(max_length=255)
    publisher = forms.CharField(max_length=128)
    publicationDate = forms.DateInput()
    
    created = forms.DateField(disabled=True)
    updated = forms.DateField(disabled=True)
    
    class Meta:
        model = books
        fields = (
            'title', 
            'orig_description', 
            'new_description', 
            'created',
            'updated',
            'authors',
            'isbn10',
            'isbn13', 
            'subject',
            'publisher',
            'publicationDate',
            ) 
        # 'userrating', 'authors'
        
    def __init__(self, *args, **kwargs):
        instance = kwargs['instance']
        if not instance.new_description:
            # never update (original) description, but store updated text in new_description
            kwargs['initial']['new_description'] = instance.description
        super(BookUpdateForm, self).__init__(*args, **kwargs)

        self.fields['new_description'].widget = forms.TextInput()
        self.fields['new_description'].label = 'Description'
        
        book_authors = [ (o.id, o.name) for o in instance.authors.all() ]
        self.fields['authors'].widget = AuthorsTagWidget(
                attrs={
                    # 'data-tags': 'true',
                    'data-placeholder': 'search for book authors',
                    'data-minimum-input-length': 2,
                    #'data-width': 'auto', # / '50em' / ...
                    },
                #dependent_fields=,
                data_url = reverse('authors_book'),
                choices=book_authors,
                userGetValTextFuncName=None,
                )
        self.fields['authors'].queryset = authors.objects.all()
        #self.fields['authors'].widget.choices = book_authors
        
        #self.fields['publicationDate'].widget = widgets.SelectDateWidget()  # years=years_tuple
        self.fields['publicationDate'].widget = widgets.DateInput()  # format=('%Y-%m-%d',)
        
        # https://stackoverflow.com/questions/46094811/change-django-required-form-field-to-false
        for field_name in ('new_description','isbn10','isbn13','subject','publisher', 'publicationDate',
                           'created', 'updated'):
            self.fields[field_name].required = False
            
        #self.fields['created'].widget = widgets.DateInput() # BUT not to be edited, readonly
        #self.fields['updated'].value = datetime.now()
            
    def clean_isbn10(self):
        data = self.cleaned_data['isbn10']
        if data and len(data) < 10:
            raise ValidationError('Invalid value for ISBN10, expect 10 digits')
        return data
    
    def clean_updated(self):
        data = self.cleaned_data['updated']
        data = datetime.now()
        return data
    
    def clean_new_description(self):
        data = self.cleaned_data['new_description']
        if self.instance.description == data:
            return None  # not changed
        return data
        
