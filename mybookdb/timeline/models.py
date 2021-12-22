"""
timeline add-on for mybookdb
record timeline events
"""
from django.db import models
from partial_date.fields import PartialDateField
from bookshelf.models import books
from django.utils.translation import gettext as _


class DatePrecision(models.TextChoices):
    EXACT_YEAR = 'YR', _('Jahr')
    EXACT_DATE = 'EX', _('Tag od Monat')
    APPROX_YEAR = 'YA', _('ca Jahr')
    APPROX_DECADE = 'DA', _('ca Jahrzehnt')
    APPROX_CENTURY = 'CA', _('ca Jahrhundert')
    APPROX_GUESSED = 'G?', _('vermutlich')
    NEAR_FUTURE = 'FN', _('nahe Zukunft')
    FAR_FUTURE = 'FF', _('ferne Zukunft')
    FUTURE = 'FU', _('Zukunft')
    NOTDETERMINED = 'ND', _('unbestimmt') # transition
    UNKNOWN = 'UN', _('unbekannt od nicht datierbar')


class timelineevent(models.Model):
    """ timeline event with optional location and comment """        
        
    book = models.ForeignKey(books, on_delete=models.CASCADE)
    date = PartialDateField()
    is_bc = models.BooleanField(default=False)
    precision = models.CharField(
        max_length=2,
        choices=DatePrecision.choices,
        default=DatePrecision.NOTDETERMINED
    )
    # TODO evaluate datautil.date.FlexiDate, but need a widget for input 
    location = models.TextField(null=True)
    comment = models.TextField(null=True)
    
    def __str__(self):
        if self.precision == 'unbestimmt': # DatePrecision.NOTDETERMINED.:
            value = '%s' % (self.date,)
        else:
            value = '%s (%s)' % (self.date, self.date_precision)
        return value
    
    @property
    def date_precision(self):
        #value = self.precision
        #value = dict(DatePrecision.choices)[self.precision]
        value = self.get_precision_display()
        return value
