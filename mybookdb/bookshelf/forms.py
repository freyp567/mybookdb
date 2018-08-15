from datetime import datetime, date
from django.core.exceptions import ValidationError
from django import forms
from django.forms import widgets

from .models import books


class BookUpdateForm(forms.ModelForm):
    """
    update book information
    """
    title = forms.CharField(max_length=255)
    description = forms.TextInput()  # TOdO required=False
    isbn10 = forms.CharField(max_length=10, min_length=10)
    isbn13 = forms.CharField(max_length=10, min_length=10)
    subject = forms.CharField(max_length=255)
    publisher = forms.CharField(max_length=128)
    publicationDate = forms.DateInput()
    
    created = forms.DateField(disabled=True)
    updated = forms.DateField(disabled=True)
    
    # TODO allow to edit authors 
    # forms.ModelMultipleChoiceField(queryset=...) ?
    
    class Meta:
        model = books
        fields = (
            'title', 
            'description', 
            'created',
            'updated',
            'isbn10',
            'isbn13', 
            'subject',
            'publisher',
            'publicationDate',
            ) 
        # 'userrating', 'authors'
        
    def __init__(self, *args, **kwargs):
        super(BookUpdateForm, self).__init__(*args, **kwargs)
        #self.fields['publicationDate'].widget = widgets.SelectDateWidget()  # years=years_tuple
        self.fields['publicationDate'].widget = widgets.DateInput()  # TODO date format
        # https://stackoverflow.com/questions/46094811/change-django-required-form-field-to-false
        for field_name in ('description','isbn10','isbn13','subject','publisher', 'publicationDate',
                           'created', 'updated'):
            self.fields[field_name].required = False
            
        #self.fields['created'].widget = widgets.DateInput()
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
