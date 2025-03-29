# MyBookDb
## Purpose
Originally concepted and implemented as replacement for the MyBookDroid application I used several years on my Android device. 
As MyBookDB was no longer updated and then disappeared, my intention was to have a replacement that can synchronize all book information maintained in MyBookDroid to a database / web application of my choice. This was the original intention behind developing a web based application that can do all MyBookDroid could (at least the part I used).

Nowadays, I no longer use MyBookDroid ... but I use BookCatalogue instead. An other Android application for storing information on books read.
So the focus of MyBookDb changed, and allows now to sync information from and to BookCatalogue. And it does it's job, with a couple of known issues like duplicate handling and ratings.

As this is a leasure time project, and leasure time is limited (I also use a lot of time to do reading, actually) advances may be slow.
I will increase functionality when I find time, with focus on what I need to keep track on the books read. 

Moreover, MyBookDb serves also for experimentation with new libraries, and to play with new technologies as GraphQL. 
With no expectation to make it complete or fully usable. 

Some things I added over time on top of what MyBookDroid was able to store (and BookCatalogue) is:
+ add links to book info, reviews, ...
+ add timeline events so I can list the books by epoche (as historical fiction is one of my favorit genre)
+ integration with german onleihe, for lookup and merkliste
+ integration with other book catalogs for checking

## GraphQL support - disabled for Django 4.0

As there currently is an issue with the graphene-django extension and Django 4, see
https://github.com/graphql-python/graphene-django/issues/1284
we decided to deactivate GraphQL support for time beeing. 
As it anyway was an experimental feature not required to use the application, it should have no serious drawbacks to do so. 
When time comes (and bugs get fixed) we will think about readding GraphQL support.

## prerequisites
+ Django 5.0 (or newer)
+ PostgreSQL (or SQLListe, formerly used but due to some performance problems replaced)
+ more prerequisites, see requirements.txt and Pipfile

External libraries (bootstrap4, bootstrap-table, ...) are used, using yarn as package manager.

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

Important: run 
```python mybookdb\manage.py collectstatic```
after changes to yarn configuration / updates.


## some TODOs
+ login and user access (currently limited to editing book details)
+ add new books with lookup book catalogues for details

