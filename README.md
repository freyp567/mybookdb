# mybookdb
a simple adaption of the (no longer maintained) MyBookDroid book list app for Django / web.
## prerequisites
+ Django 2.0  (2.0.3 or newer)
+ PostgreSQL (or compatible database)
+ more prerequisites, see pipenv.lock

## configuration
See Django settings.

## TODOs
+ cleanup of imported tata (from MyBookDroid sqllite backup) - umlaite, incomplete info, groups, ...
+ bootstrap4 integration with django-bootstrap4
  but which approach to choose? see:
  https://github.com/zostera/django-bootstrap4
  https://github.com/nikolas/django-bootstrap4-1
  https://github.com/GabrielUlici/django-bootstrap4
  http://django-bootstrap.readthedocs.io/en/latest/history.html
  https://github.com/django-crispy-forms/django-crispy-forms/issues/732

+ explore:
  replace django-tables2 by bootstrap-tables?
  if yes, how to render them the django way?

+ search for / in book title
+ table filtering (would be for free using bootstrap-tables)
+ editing book details
