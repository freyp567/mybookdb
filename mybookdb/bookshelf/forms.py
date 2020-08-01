# -*- coding: utf-8 -*-
from datetime import datetime
from pyisbn import Isbn13, Isbn10, IsbnError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
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


BOOK_LANGUAGE = [
    ('--', _('unknown')),
    ('de', _('German')),
    ('en', _('English')),
    ('fr', _('French')),
    ('xx', _('other language')),
]

def get_lang_code(lang):
    if not lang:
        return '--'
    elif lang not in ('de', 'fr', 'en'):
        return 'xx'
    else:
        return lang

def get_lang_text(lang):
    for item in BOOK_LANGUAGE:
        if item[0] == lang:
            return item[1]
    return _('unknown')



class BookCreateForm(forms.ModelForm):
    """
    create book information
    """
    title = forms.CharField(max_length=255)
    unified_title = forms.CharField(max_length=255, label=_('Buchtitel'))
    book_serie = forms.CharField(strip=True)
    orig_description = forms.CharField(disabled=True, label="Original description")
    new_description = forms.CharField()
    isbn13 = forms.CharField(max_length=13, min_length=13)
    language = forms.ChoiceField(choices=BOOK_LANGUAGE)
    
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
            'unified_title', 
            'book_serie',
            'orig_description', 
            'new_description', 
            'created',
            'updated',
            'authors',
            'isbn13', 
            'language',
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
            Fieldset(
                '',
                Field('title'),
                Field('unified_title'),
                Field('book_serie'),
                Div(
                    Div(Field('updated', readonly=True), css_class='col-md-4',),
                    Div(Field('created', readonly=True), css_class='col-md-4',),
                    Div('publicationDate', css_class='col-md-4',),
                    css_class='row',
                ),
                Div(
                    Div(Field('isbn13'), css_class='col-md-6',),
                    Div(Field('language'), css_class='col-md-6',),
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
        self.fields['language'].initial = settings.DEFAULT_LANGUAGE
        
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
        
        self.fields['publicationDate'].widget = widgets.DateInput()
        
        # https://stackoverflow.com/questions/46094811/change-django-required-form-field-to-false
        for field_name in ('new_description','isbn13','subject','publisher', 'publicationDate',
                           'created', 'updated', 'unified_title', 'book_serie'):
            self.fields[field_name].required = False


    def clean(self):
        isbn13_value = self.cleaned_data.get('isbn13')
        isbn13 = isbn13_value and Isbn13(isbn13_value)        
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

    def clean_language(self):
        lang = self.cleaned_data['language']
        if lang is '--':
            return None
        else:
            return lang
    
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
    unified_title = forms.CharField(max_length=255)
    book_serie = forms.CharField(max_length=255)
    orig_description = forms.CharField(disabled=True, label="Original description")
    new_description = forms.CharField()
    isbn13 = forms.CharField(max_length=13, min_length=13)
    
    language = forms.ChoiceField(choices=BOOK_LANGUAGE)
    
    authors = forms.ModelMultipleChoiceField(
        queryset=authors.objects.none(), 
    )
    
    subject = forms.CharField(max_length=255)
    publisher = forms.CharField(max_length=128)
    publicationDate = forms.DateInput()
    
    created = forms.DateField(disabled=True)
    updated = forms.DateField(disabled=True)
    userRating = forms.IntegerField(max_value=5, min_value=1)

    read_start = forms.DateField(disabled=False)
    read_end = forms.DateField(disabled=False)
    
    class Meta:
        model = books
        fields = (
            'title', 
            'unified_title',
            'book_serie',
            'orig_description', 
            'new_description', 
            'created',
            'updated',
            'read_start',
            'read_end',
            'authors',
            'isbn13', 
            'language',
            'subject',
            'publisher',
            'publicationDate',
            'userRating',
            ) 
        
    def __init__(self, *args, **kwargs):
        instance = kwargs['instance']
        if not instance.new_description:
            # never update (original) description, but store updated text in new_description
            kwargs['initial']['new_description'] = instance.description
        super(BookUpdateForm, self).__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.label_class = 'lb-sm'
        
        book_id = instance and instance.id or 0
        if book_id:
            cancel_url = reverse('bookshelf:books-detail', args=(book_id,))
            # self.helper.form_action = cancel_url  # parameters? .form_action fails with render(...) for resolved url
        else:
            # TODO referer_url ??
            cancel_url = reverse('bookshelf:index',)

        self.helper.layout = Layout(
            # Alert(...)
            Fieldset(
                '',
                Field('title'),
                Div(
                    Div(Field('unified_title', width=125), css_class='col-md-6'),
                    Div(Field('book_serie', width=125), css_class='col-md-6'),
                    css_class='row',
                ),
                Div(
                    Div(Field('updated', readonly=True), css_class='col-md-4',),
                    Div(Field('created', readonly=True), css_class='col-md-4',),
                    Div('publicationDate', css_class='col-md-4',),
                    css_class='row',
                ),
                Div(
                    Div(Field('read_start'), css_class='col-md-4',),
                    Div(Field('read_end'), css_class='col-md-4',),
                    css_class='row',
                ),
                Div(
                    Div(Field('isbn13'), css_class='col-md-6',),
                    Div(Field('language'), css_class='col-md-6',),
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
                ),
            Div( # TODO move to single row
                Div(Field('userRating'), css_class='col-md-2'),
                Div(Field('subject'), css_class='col-md-10'),
                css_class='row',
                ),
            FormActions(
                Submit('save', 'Save changes'),
                Button(
                    'cancel', 'Cancel', css_class = 'btn',
                    onclick="window.location.href='{}';".format(cancel_url),
                )
            )
        )

        self.fields['new_description'].widget = forms.Textarea(attrs={'cols': 80, 'rows': 6})
        self.fields['orig_description'].widget = forms.Textarea(attrs={'cols': 80, 'rows': 6})
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
        #self.fields['authors'].required = True
        
        self.fields['publicationDate'].widget = widgets.DateInput()  # format=('%Y-%m-%d',)
        self.fields['read_start'].widget = widgets.DateInput()
        self.fields['read_end'].widget = widgets.DateInput()
        
        # https://stackoverflow.com/questions/46094811/change-django-required-form-field-to-false
        for field_name in ('new_description','isbn13','subject','publisher', 'publicationDate',
                           'created', 'updated', 'unified_title', 'book_serie', 'userRating'):
            self.fields[field_name].required = False


    def clean(self):
        return self.cleaned_data
        
    def clean_updated(self):
        data = self.cleaned_data['updated']
        data = datetime.now(tz=timezone.utc)
        return data
    
    def clean_new_description(self):
        data = self.cleaned_data['new_description']
        return data
    
    def clean_language(self):
        lang = self.cleaned_data['language']
        if lang is '--':
            return None
        else:
            return lang
        
    def orig_description(self):
        data = self.cleaned_data['orig_description']
        return data or ''


class BookInfoForm(forms.ModelForm):
    """
    show book information
    """
    book_title = forms.CharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 1}))
    book_serie = forms.CharField()
    
    class Meta:
        model = books
        fields = (
            'book_title',
            'book_serie',
            )
        
    def __init__(self, *args, **kwargs):
        super(BookInfoForm, self).__init__(*args, **kwargs)
        # TODO use crispy_forms
        self.fields['book_title'].widget.attrs['disabled'] = 'disabled' # readonly
        if kwargs.get('instance'):
            book = kwargs['instance']
            self.fields['book_title'].initial = book.book_title
        self.fields['book_serie'].widget.attrs['disabled'] = 'disabled'


class AuthorCreateForm(forms.ModelForm):
    
    class Meta:
        model = authors
        fields = (
            'name', 
            'familyName',
            'updated', 
            'short_bio',
            ) 

    name = forms.CharField(max_length=255, label='Vorname Name')
    familyName = forms.CharField(max_length=255, label='Familienname')
    updated = forms.DateField(disabled=True)    
    short_bio = forms.CharField(label=_('Kurzbiografie'))
        
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
                Field('short_bio'),
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
        
        self.fields['short_bio'].widget = forms.Textarea(attrs={'rows': 4}) # 'cols': 80, 
        self.fields['updated'].initial = datetime.now(tz=timezone.utc)



    def clean(self):
        return self.cleaned_data

    def clean_updated(self):
        data = self.cleaned_data['updated']
        if data is None:
            data = datetime.now(tz=timezone.utc)
        return data
    
        
class AuthorUpdateForm(AuthorCreateForm):

    def __init__(self, *args, **kwargs):
        super(AuthorUpdateForm, self).__init__(*args, **kwargs)


class StateUpdateForm(forms.ModelForm):
    """
    update book state
    see states_form.html
    """

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
    private = forms.BooleanField(
        required=False, initial=False, 
        help_text='private')
    obsolete = forms.BooleanField(
        required=False, initial=False, 
        help_text='obsolete')
    
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
            'private',
            'obsolete',
            )

    def __init__(self, *args, **kwargs):
        assert 'instance' in kwargs, "missing state obj"  # always need state obj to update (create is implicit)
        super(StateUpdateForm, self).__init__(*args, **kwargs)
        
        self.fields['toBuy'].label = 'wishlist (to buy)'  # TODO toBuy vs wantRead, have both in form
        self.fields['iOwn'].label = 'not read or stopped reading (I own)'
        self.fields['private'].label = 'private'
        self.fields['obsolete'].label = 'obsolete / to be removed'

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


class BookExportForm(forms.Form):
    
    EXPORTTYPES = [
        ('serialized', 'Django-Serialisiert'),
        ('bookcatalog-csv', 'CSV für Book Catalogue'),        
    ]
    export_type = forms.ChoiceField(choices=EXPORTTYPES, )
    export_path = forms.CharField()
    
    def __init__(self, *args, **kwargs):
        super(BookExportForm, self).__init__(*args, **kwargs)

        self.fields['export_type'].initial = 'serialized'
        self.fields['export_path'].initial = 'books_%s' % datetime.now().strftime("%Y-%m-%d")

