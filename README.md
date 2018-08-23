# mybookdb
A simple adaption of the MyBookDroid book list app for android  (no longer maintained, unfortunately).

Long term vision is to replace MyBookDroid by a web-based application available from everywhere.
But due to limited time for this personal / educational project, the approach is to build up the mybookdb 
web app step by step into this direction, but not replacing MyBookDroid in short term so focus is on searching.
For import of the book database, a migration script will allow to import the book data from .csv exports 
from MyBookDroid repeatedly (and hopefully lossless).

## prerequisites
+ Django 2.0  (2.0.3 or newer)
+ SQLLite (or PostgreSQL)
+ more prerequisites, see pipenv.lock

External libraries (bootstrap4, bootstrap-table, ...) are provided locally (but that may be changed in future
depending on deployment tools and strategy when reaching this stage).

## configuration
See Django settings.

## TODOs
+ show states in book-detail
+ cleanup of imported data (from MyBookDroid sqllite backup) - umlaute, incomplete info, groups, ...
+ login and user access
+ editing book details

