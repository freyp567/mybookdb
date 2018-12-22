"""
Bookmarks forms
"""

from datetime import datetime

from django import forms
from django.forms import widgets
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from bookmarks.models import author_links, book_links, linksites

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Field, Div, Button
from crispy_forms.bootstrap import FormActions


LINK_STATUS_CHOICES = (
    ('ok', _("ok")),
    ('stale', _("stake")),
    ('broken', _("broken")),
)


class BookmarkCreateForm(forms.ModelForm):
    
    class Meta:
        # model = author_links
        fields = (
            'link_name', 
            'link_site', 
            'link_uri',
            'link_state',
            'created',
            'updated',
            #'verified'
            )

    def __init__(self, *args, **kwargs):
        self.obj_type = kwargs.pop('objtype')
        self.obj_id = kwargs.pop('pk')
        if self.obj_type == 'books':
            self._meta.model = book_links
        else:
            self._meta.model = author_links
        super(BookmarkCreateForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.label_class = 'lb-sm'
        
        self.helper.layout = Layout(
            # Alert(...)
            Fieldset(
                '',
                Div(
                    Field('link_uri'),
                ),
                Div(
                    Field('link_name', css_class='col-md-4',),
                    Field('link_site', css_class='col-md-4',),
                ),
                Div(
                    Div(Field('link_state'), css_class='col-md-4',),
                    Div(Field('updated', readonly=True), css_class='col-md-4',),
                    Div(Field('created', readonly=True), css_class='col-md-4',),
                    css_class='row',
                ),
            ),
            FormActions(
                Submit('save', 'Save changes'),
                Button( 'cancel', 'Cancel', css_class = 'btn btn-default',
                        onclick="window.history.back()")
            )
        )
        
        self.fields['link_name'] = forms.CharField(max_length=128)
        
        self.fields['link_site'] = forms.ChoiceField(
            choices=self._link_site_choices(),
            required=True
            ) # values from linktargets

        self.fields['link_state'] = forms.ChoiceField(
            choices=LINK_STATUS_CHOICES, 
            label="Status", initial='ok', 
            widget=forms.Select(), 
            required=True)

        self.fields['link_uri'] = forms.URLField()

        #link_name = models.TextField(null=False)  # short name describing link
        #verified = models.DateField(null=True)

        self.fields['created'] = forms.DateField(disabled=True, initial=datetime.now())
        self.fields['updated'] = forms.DateField(disabled=True, initial=datetime.now())


    def _link_site_choices(self):
        choices = []
        for site in linksites.objects.all():
            choices.append(( site.id, site.name ))
        return choices

    def save(self, commit=True):
        # prepare save
        instance = super().save(False)
        if self.obj_type == 'authors':
            # associate new lnk with author 
            instance.author_id = self.obj_id
        else:
            instance.book_id = self.obj_id
        # set book or author reverse foreign key from the link model
        # instance.xyz_set.add(self.cleaned_data['refobj']))  # TODO
        instance = super().save(commit)
        return instance
    
    def clean_created(self):
        if not self.cleaned_data['created']:
            return datetime.now(tz=timezone.utc)
        else:
            return self.cleaned_data['created']
        
    def clean_updated(self):
        return datetime.now(tz=timezone.utc)
        
    def clean(self):
        for field_name in ('created', 'updated', 'verified'):
            self.cleaned_data[field_name] = datetime.now(tz=timezone.utc)

        uri = self.cleaned_data['link_uri']
        if self.obj_type == 'authors':
            found = author_links.objects.filter(link_uri = uri)
        else:
            found = book_links.objects.filter(link_uri = uri)
            
        if found:
            raise ValidationError("bookmark does already exist")
        
        return self.cleaned_data
        
        
    