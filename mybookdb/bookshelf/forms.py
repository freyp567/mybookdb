from datetime import datetime, date
from pyisbn import Isbn13, Isbn10, IsbnError

from django.core.exceptions import ValidationError
from django.urls import reverse, reverse_lazy
from django import forms
from django.forms import widgets
#from django.forms.models import inlineformset_factory
from django.utils.translation import gettext as _
from django.utils import timezone

from bookshelf.models import books, authors, states
from bookshelf.widgets import AuthorsTagWidget

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Field, Div, Button
from crispy_forms.bootstrap import FormActions, TabHolder, Tab



class BookCreateForm(forms.ModelForm):
    """
    create book information
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
    publicationDate = forms.fields.DateField(  # input_formats
        widget=forms.widgets.DateInput(attrs={'type': 'date'}),
    )
    
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
        # 'userrating',
        
    def __init__(self, *args, **kwargs):
        super(BookCreateForm, self).__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.label_class = 'lb-sm'
        
        self.helper.layout = Layout(
            # Alert(...)
            Fieldset(
                '',
                Field('title'),
                Div(
                    Div(Field('updated', readonly=True), css_class='col-md-4',),
                    Div(Field('created', readonly=True), css_class='col-md-4',),
                    Div('publicationDate', css_class='col-md-4',),
                    css_class='row',
                ),
                Div(
                    Div(Field('isbn13'), css_class='col-md-6',),
                    Div(Field('isbn10'), css_class='col-md-6',),
                    css_class='row',
                ),
            ),
            TabHolder(
                Tab('description',
                    Field('new_description', label='')
                    ), 
                Tab('orig-description',
                    Field('orig_description', readonly=True, title='imported description')
                    ),
                ),
            Div(
                'authors',
                'subject',
                ),
            FormActions(
                Submit('save', 'Save changes'),
                Button( 'cancel', 'Cancel', css_class = 'btn btn-default',
                        onclick="window.history.back()")
            )
        )

        self.fields['new_description'].widget = forms.Textarea(attrs={'cols': 80, 'rows': 7})
        self.fields['new_description'].label = False
        self.fields['orig_description'].label = False
        
        book_authors = []
        self.fields['authors'].widget = AuthorsTagWidget(
                attrs={
                    'data-placeholder': 'search for book authors',
                    'data-minimum-input-length': 2,
                    'data-tags': False,  # prevent dynamic tag creation
                    'data-width': '50%',  # 'auto' / '50em' / ...
                    },
                #dependent_fields=,
                data_url = reverse('bookshelf:authors_book'),
                choices=book_authors,
                userGetValTextFuncName=None,
                )
        self.fields['authors'].queryset = authors.objects.all()
        #self.fields['authors'].required = False
        #self.fields['authors'].widget.choices = book_authors
        
        #self.fields['publicationDate'].widget = widgets.SelectDateWidget()  # years=years_tuple
        self.fields['publicationDate'].widget = widgets.DateInput()  # format=('%Y-%m-%d',)
        
        # https://stackoverflow.com/questions/46094811/change-django-required-form-field-to-false
        for field_name in ('new_description','isbn10','isbn13','subject','publisher', 'publicationDate',
                           'created', 'updated'):
            self.fields[field_name].required = False

        #self.fields['created'].widget = widgets.DateInput() # BUT not to be edited, readonly
        #self.fields['updated'].value = datetime.now(tz=timezone.utc)


    def clean(self):
        isbn10_value = self.cleaned_data.get('isbn10')
        isbn13_value = self.cleaned_data.get('isbn13')
        isbn10 = isbn10_value and Isbn10(isbn10_value)
        isbn13 = isbn13_value and Isbn13(isbn13_value)
        if isbn13:
            if isbn10 is None:
                self.cleaned_data['isbn10'] = isbn13.convert()
            elif isbn10 != isbn13.convert():
                self.add_error('isbn10', 'does not match value for ISBN13')
        
        return self.cleaned_data
    
    def clean_title(self):
        data = self.cleaned_data['title']
        if not data:
            self.add_error('title', 'must have title')
        return data
    
    def clean_isbn13(self):
        data = self.cleaned_data['isbn13']
        if not data:
            return None
        try:
            isbn13 = Isbn13(data)
        except IsbnError as err:
            raise ValidationError("not a valid ISBN13 - %s" % err)
        if not isbn13.validate():
            self.add_error('isbn13', 'ISBN13 not valid')
        return data
        
    def clean_isbn10(self):
        data = self.cleaned_data['isbn10']
        if not data:
            return None
        try:
            isbn10 = Isbn10(data)
        except IsbnError as err:
            raise ValidationError("not a valid ISBN10 - %s" % err)
        if not isbn10.validate():
            self.add_error('isbn10', 'ISBN10 not valid')
        #if data and len(data) < 10:
        #    raise ValidationError('Invalid value for ISBN10, expect 10 digits')
        return data
    
    def clean_updated(self):
        data = self.cleaned_data['updated']
        if data is None:
            data = datetime.now(tz=timezone.utc)
        return data
    
    def clean_created(self):
        data = self.cleaned_data['created']
        if data is None:
            data = datetime.now(tz=timezone.utc)
        return data
    
    def clean_new_description(self):
        data = self.cleaned_data['new_description']
        if self.instance.description == data:
            return None  # not changed
        return data

    def clean_publicationDate(self):
        data = self.cleaned_data['publicationDate']
        #if data and len(data) == 4 and data.isdigit():
        #    # numeric value e.g. '2018', but expect date 
        #   data += '-01-01'
        return data
    
    def orig_description(self):
        data = self.cleaned_data['orig_description']
        if not data:
            self.add_error('orig_description', 'must have description')
        return data or ''


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
        
        self.helper = FormHelper()
        #self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'lb-sm'
        #self.helper.field_class = 'col-lg-8'
        
        # TODO show validation messages (when returning after save failed)
        
        self.helper.layout = Layout(
            # Alert(...)
            Fieldset(
                '',
                Field('title'),
                Div(
                    Div(Field('updated', readonly=True), css_class='col-md-4',),
                    Div(Field('created', readonly=True), css_class='col-md-4',),
                    Div('publicationDate', css_class='col-md-4',),
                    css_class='row',
                ),
                Div(
                    Div(Field('isbn13'), css_class='col-md-6',),
                    Div(Field('isbn10'), css_class='col-md-6',),
                    css_class='row',
                ),
            ),
            TabHolder(
                Tab('description',
                    Field('new_description', label='')
                    ), 
                Tab('orig-description',
                    Field('orig_description', readonly=True, title='imported description')
                    ),
                ),
            Div(
                'authors',
                'subject',
                ),
            FormActions(
                Submit('save', 'Save changes'),
                Button( 'cancel', 'Cancel', css_class = 'btn btn-default',
                        onclick="window.history.back()")
            )
        )

        self.fields['new_description'].widget = forms.Textarea(attrs={'cols': 80, 'rows': 7})
        self.fields['new_description'].label = False
        self.fields['orig_description'].label = False
        
        book_authors = [ (o.id, o.name) for o in instance.authors.all() ]
        self.fields['authors'].widget = AuthorsTagWidget(
                attrs={
                    'data-tags': False,
                    'data-placeholder': 'search for book authors',
                    'data-minimum-input-length': 2,
                    'data-width': '50%',  # auto' / '50em' / ...
                    },
                #dependent_fields=,
                data_url = reverse('bookshelf:authors_book'),
                choices=book_authors,
                userGetValTextFuncName=None,
                )
        self.fields['authors'].queryset = authors.objects.all()
        #self.fields['authors'].required = False
        #self.fields['authors'].widget.choices = book_authors
        
        #self.fields['publicationDate'].widget = widgets.SelectDateWidget()  # years=years_tuple
        self.fields['publicationDate'].widget = widgets.DateInput()  # format=('%Y-%m-%d',)
        
        # https://stackoverflow.com/questions/46094811/change-django-required-form-field-to-false
        for field_name in ('new_description','isbn10','isbn13','subject','publisher', 'publicationDate',
                           'created', 'updated'):
            self.fields[field_name].required = False

        #self.fields['created'].widget = widgets.DateInput() # BUT not to be edited, readonly
        #self.fields['updated'].value = datetime.now(tz=timezone.utc)


    #def clean(self):
    
    def clean_isbn10(self):
        data = self.cleaned_data['isbn10']
        if data and len(data) < 10:
            raise ValidationError('Invalid value for ISBN10, expect 10 digits')
        return data
    
    def clean_updated(self):
        data = self.cleaned_data['updated']
        data = datetime.now(tz=timezone.utc)
        return data
    
    def clean_new_description(self):
        data = self.cleaned_data['new_description']
        return data
    
    def orig_description(self):
        data = self.cleaned_data['orig_description']
        return data or ''


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
        self.fields['title'].widget = forms.Textarea(attrs={'cols': 80, 'rows': 1})
        self.fields['title'].widget.attrs['disabled'] = 'disabled'
    
#BookInfoFormSet = inlineformset_factory(states, books, extra=0)


#class BookStatusUpdateForm(forms.ModelForm):


class AuthorCreateForm(forms.ModelForm):
    
    class Meta:
        model = authors
        fields = (
            'name', 
            'updated', 
            ) 

    name = forms.CharField(max_length=255, label='Vorname Name')
    #familyName = forms.CharField(max_length=255, label='Familienname')
    updated = forms.DateField(disabled=True)    
        
    def __init__(self, *args, **kwargs):
        super(AuthorCreateForm, self).__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.label_class = 'lb-sm'

        self.helper.layout = Layout(
            # Alert(...)
            Fieldset(
                '',
                Field('name'),
                Field('familyName'),
                ),
            Div(
                Div(Field('updated', readonly=True), css_class='col-md-4',),
                css_class='row',
            ),            
            FormActions(
                Submit('save', 'Save changes'),
                Button( 'cancel', 'Cancel', css_class = 'btn btn-default',
                        onclick="window.history.back()")
            )            
        )
        
        self.fields['updated'].initial = datetime.now(tz=timezone.utc)



    def clean(self):
        return self.cleaned_data

    def clean_updated(self):
        data = self.cleaned_data['updated']
        if data is None:
            data = datetime.now(tz=timezone.utc)
        return data
        
        
class AuthorUpdateForm(AuthorCreateForm):
    # TODO differentiate create / update? if, then factor out validations ... to shared base class

    def __init__(self, *args, **kwargs):
        super(AuthorUpdateForm, self).__init__(*args, **kwargs)


class StateUpdateForm(forms.ModelForm):  # TODO integrate into edit form for book
    """
    update book state
    """
    # TODO
    # inline formset 
    # https://docs.djangoproject.com/en/dev/topics/forms/modelforms/#inline-formsets
    # https://stackoverflow.com/questions/1113047/creating-a-model-and-related-models-with-inline-formsets
    #
    # or implement as new standalone form

    favorite = forms.BooleanField(
        required=False, initial=False, 
        label=_("my Favorite"),
        help_text='to flag favorite book (read or unread)')
    toRead = forms.BooleanField(
        required=False, initial=False, 
        label=_("to read"),
        help_text='candidate to read, and available')
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
            'toBuy',  # = on wishlist
            'toRead',
            'readingNow',
            'haveRead',
            # 'wantRead',
            'iOwn',   # = not read / suspended (stopped reading / partially read)            
            )

    def __init__(self, *args, **kwargs):
        assert 'instance' in kwargs, "missing state obj"  # always need state obj to update (create is implicit)
        super(StateUpdateForm, self).__init__(*args, **kwargs)
        
        for field_name in self.fields:
            #self.fields[field_name].widget = CheckboxInput()
            #self.fields[field_name].widget.attrs['class'] = 'form-control form-control-lg'
            pass
        
        self.fields['toBuy'].label = 'wishlist (to buy)'  # TODO toBuy vs wantRead, have both in form
        self.fields['iOwn'].label = 'not read or stopped reading (I own)'

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
            raise ValidationError("either have read or currently reading")
        if haveRead and toRead:
            raise ValidationError("either read or to be read")
        if readingNow and toRead:
            raise ValidationError("either currently reading or to be read")
        return cleaned_data