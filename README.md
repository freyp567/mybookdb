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

To untegrate with LibraryThing, you will need to pass the LT API Key by setting the environment variable LIBRARYTHING_APIKEY.
and take care that you fullfill the licensing requirments listed in LibraryThing API wiki (non-commercial use, not more than one request per second, ...).
For details see https://wiki.librarything.com/index.php/LibraryThing_APIs.

## packaging
Using yarn / django-yarnpkg for packaging Javascript components (bootstrap4, jquery).
Expect yarn to be installed externally / globally.

## TODOs
+ state handling cleanup, make cancel button work
+ cleanup of imported data (from MyBookDroid sqllite backup) - umlaute, incomplete info, groups, ...
+ login and user access (currently only limited to editing book details)
+ editing book details: more fields to add
+ wishlist feature (list of books I want to read - an extended onleihe Merkzettel, covering also Audible)
+ add more features, e.g. to add new books with lookup book catalogues for details

