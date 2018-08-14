from django.core.exceptions import ValidationError
from django import forms

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
    
    
    class Meta:
        model = books
        fields = (
            'title', 
            'description', 
            'isbn10',
            'isbn13', 
            'subject',
            'publisher',
            'publicationDate',
            ) 
        # 'userrating', 'authors'
    
    def clean_isbn10(self):
        data = self.cleaned_data['isbn10']
        if len(data) < 10:
            raise ValidationError('Invalid value for ISBN10, expect 10 digits')
        return data
