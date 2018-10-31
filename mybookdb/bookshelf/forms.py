from datetime import datetime, date
from django.core.exceptions import ValidationError
from django.urls import reverse, reverse_lazy
from django import forms
from django.forms import widgets
#from django.forms.models import inlineformset_factory
from django.utils.translation import gettext as _

from bookshelf.models import books, authors, states
from bookshelf.widgets import AuthorsTagWidget


class BookUpdateForm(forms.ModelForm):
    """
    update book information
    """
    title = forms.CharField(max_length=255)
    orig_description = forms.CharField(disabled=True, label="Original description")
    new_description = forms.CharField()
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

        self.fields['new_description'].widget = forms.Textarea(attrs={'cols': 80, 'rows': 5})
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


    #def clean(self):
    
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


class BookInfoForm(forms.ModelForm):
    """
    show book information
    """
    title = forms.CharField(max_length=255)  # TODO readonly
    
    class Meta:
        model = books
        fields = (
            'title', 
            )
        
    def __init__(self, *args, **kwargs):
        super(BookInfoForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs['disabled'] = 'disabled'
    
#BookInfoFormSet = inlineformset_factory(states, books, extra=0)

class StateUpdateForm(forms.ModelForm):  # TODO integrate into edit form for book
    """
    update book state
    """
    # TODO correlate state with book (OneToOne relationship)
    # see https://stackoverflow.com/questions/27832076/modelform-with-onetoonefield-in-django
    #
    # inline formset 
    # https://docs.djangoproject.com/en/dev/topics/forms/modelforms/#inline-formsets
    # https://stackoverflow.com/questions/1113047/creating-a-model-and-related-models-with-inline-formsets
    #
    # or implement as new standalone form
    # TODO fix initialization
    favorite = forms.BooleanField(
        required=False, initial=False, 
        label=_("my Favorite"),
        help_text='to flag favorite book (read or unread)')
    toRead = forms.BooleanField(
        required=False, initial=False, 
        label=_("to read"),
        help_text='book on wishlist, to read')
    readingNow = forms.BooleanField(
        required=False, 
        initial=False, 
        label=_("currently reading"),
        help_text='currently reading (active or suspended)')
    haveRead = forms.BooleanField(
        required=False, initial=False, 
        label=_("have read"),
        help_text='have read')
    
    class Meta:
        model = states
        fields = (
            'favorite',
            'toRead',
            'readingNow',
            'haveRead',
            )

    def __init__(self, *args, **kwargs):
        super(StateUpdateForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(StateUpdateForm, self).clean()
        haveRead = cleaned_data.get('haveRead')
        
        # validate to disallow certain combinations
        haveRead = cleaned_data.get('haveRead')
        readingNow = cleaned_data.get('readingNow')
        iOwn = cleaned_data.get('iOwn')
        toBuy = cleaned_data.get('toBuy')
        toRead = cleaned_data.get('toRead')
        if haveRead and readingNow:
            raise ValidationError("either read or currently reading")
        if haveRead and toRead:
            raise ValidationError("either read or to be read")
        if readingNow and toRead:
            raise ValidationError("either currently reading or to be read")
        # return cleaned_data