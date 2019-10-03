"""
drop all timeline events in database
(note: was unable to use truncate table timeline_events from manage.py dbshell)
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from timeline.models import bookevent

import os
import io
import copy
from datetime import datetime, date
#import sqlite3

class Command(BaseCommand):
    help = 'truncate table timeline_events'

    def handle(self, *args, **options):
        # dbpath = options['xxx']
        self.stdout.write(f"struncate table timeline_events")
        bookevent.objects.all().delete()


