from django import forms
from django.forms import widgets
#from django.forms.models import inlineformset_factory
import partial_date
from django.utils.translation import gettext as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Field, Div, Button
from crispy_forms.bootstrap import FormActions, TabHolder, Tab

from timeline.models import timelineevent


class BookEventCreateForm(forms.ModelForm):
    """ add timeline event to current book """

    date = partial_date.PartialDateField()
    book_id = forms.CharField(widget=forms.HiddenInput())    
    location = forms.CharField(required=False)
    comment = forms.CharField(widget=forms.Textarea(), required=False)  # columns=60, rows=5

    class Meta:
        model = timelineevent
        fields = (
            "book_id", "date", "is_bc", "precision", "location", "comment"
        )

    def __init__(self, *args, **kwargs):
        super(BookEventCreateForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.label_class = 'lb-sm'
        
        self.helper.layout = Layout(
            Fieldset(
                '',
                Field('date'),
                Field('is_bc'),
                Field('precision'),
                Field('location'),
                Field('comment', label=_('comment'))
            ),
            ButtonHolder(
                Submit('save', 'Save timeline event'),
            )
        )

"""
            FormActions(
                Submit('save', 'Save date/location'),
                Button( 'cancel', 'Cancel', css_class = 'btn btn-default',
                        onclick="window.history.back()")
            )

"""


class BookEventDeleteForm(forms.Form):
    """ delete timeline event to current book """

    book_id = forms.CharField(widget=forms.HiddenInput())    

    class Meta:
        model = timelineevent
    
    def __init__(self, *args, **kwargs):
        super(BookEventDeleteForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.label_class = 'lb-sm'
        
        self.helper.layout = Layout(
            Fieldset(
                '',
                Field('date'),
                Field('is_bc'),
                Field('location'),
                Field('comment', label=_('comment'))
            ),
            ButtonHolder(
                Submit('save', 'Save timeline event'),
            )
        )
