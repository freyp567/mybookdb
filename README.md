# mybookdb
A simple replacement of the MyBookDroid book list app for android  (no longer maintained, unfortunately).
As implementation ongoing, and currently far from beeing feature complete, rather to use as complement to MyBookDroid, that is still running on Android 8.

Long term vision is to replace MyBookDroid by a web-based application available from everywhere.
But due to limited time for this personal / educational project, the approach is to build up the mybookdb 
web app step by step into this direction, but not replacing MyBookDroid in short term so focus is on searching.
For import of the book database, a migration script will allow to import the book data from .csv exports 
from MyBookDroid repeatedly (and hopefully lossless).

## prerequisites
+ Django 2.0  (2.0.8 or newer)
+ SQLLite (or PostgreSQL)
+ more prerequisites, see requirements / Pipfile

External libraries (bootstrap4, bootstrap-table, ...) are provided locally (but that may be changed in future
depending on deployment tools and strategy when reaching this stage).

## configuration
See Django settings.
The following environment variables have to be set additionally before starting the Django app:#
SECRET_KEY  (no longer in settings.py for security reason)

## TODOs
+ show states in book-detail
+ cleanup of imported data (from MyBookDroid sqllite backup) - umlaute, incomplete info, groups, ...
+ login and user access (currently only limited to editing book details)
+ editing book details: more fields to add
+ add more features, e.g. to add new books with lookup book catalogues for details

