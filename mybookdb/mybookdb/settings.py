"""
Django settings for mybookdb project.

Generated by 'django-admin startproject' using Django 2.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
from pathlib import Path
#import logging
#from django.templatetags.static import static


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
#SECRET_KEY = '2z%$p8%)44alqp=a*_!)hb$-3#s0x1!lw@6x$l5ydii^l^iukc'
SECRET_KEY = os.environ["SECRET_KEY"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", False)

ALLOWED_CIDR_NETS = os.environ.get('ALLOWED_CIDR_NETS')
if not ALLOWED_CIDR_NETS:
    pass #ALLOWED_HOSTS = ['*']
else:
    ALLOWED_CIDR_NETS = ALLOWED_CIDR_NETS.split(',')
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(',')


PROMETHEUS_METRICS_EXPORT_PORT = 8001
#PROMETHEUS_METRICS_EXPORT_ADDRESS = os.environ.get('PROMETHEUS_METRICS_EXPORT_ADDRESS') or ''

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bookshelf.apps.BookshelfConfig',
    'bookmarks.apps.BookmarksConfig',
    'timeline.apps.TimelineConfig',
    'bootstrap4',
    'django_tables2',
    'django_filters',
    'django_select2',
    'graphene_django',
    'django_extensions',
    'crispy_forms',
    # 'django_prometheus',  # troubles if deployed in Docker container
    'mybookdb',
]
USE_DEBUG_TOOLBAR =os.environ.get("USE_DEBUG_TOOLBAR", False)
if USE_DEBUG_TOOLBAR:
    INSTALLED_APPS.append('debug_toolbar')
    

CRISPY_TEMPLATE_PACK = 'bootstrap4'
CRISPY_FAIL_SILENTLY = not DEBUG

# 2018-10-23 dropped django_graphiql, seems to be deprecated and outdated
# and replaced completely by graphene_django
# use graphene-django to integrate GraphiQL into Django project

STATICFILES_FINDERS = [
    'mybookdb.finders.YarnFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

YARN_ROOT_PATH = os.path.abspath(os.path.join(BASE_DIR, '..'))
print("YARN_ROOT_PATH=" + YARN_ROOT_PATH)
YARN_EXECUTABLE_PATH = os.environ.get("YARN_EXECUTABLE_PATH")

#YARN_STATIC_FILES_PREFIX = ''
#YARN_FINDER_USE_CACHE

YARN_FILE_PATTERNS = {
    'jquery': [Path('dist') / '*'],
    'js.cookie': [Path('dst') / '*'],
    'jquery-form': [Path('dist') / '*'],
    'bootstrap': [Path('dist') / '*'],
    'bootstrap-table': [Path('dist') / '*'],
    'x-editable': [Path('dist') / '*'],
    '@popperjs': [Path('core') / 'dist' / '*'],
    'clipboard': [Path('dist') / '*'],
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # 'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allow_cidr.middleware.AllowCIDRMiddleware',
    # 'django_prometheus.middleware.PrometheusAfterMiddleware',
]

if USE_DEBUG_TOOLBAR:
    # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#enabling-middleware
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'mybookdb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['./templates',],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': True,
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mybookdb.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

USE_SQLLITE = False
if USE_SQLLITE:
    DATABASES = {
        'default': {
            # 'ENGINE': 'django.db.backends.sqlite3',
            # 'ENGINE': 'django_prometheus.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:    
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.environ.get("DB_NAME", 'mybookdb'),
            'USER': os.environ.get("DB_USER", 'mybookdbusr'),
            'PASSWORD': os.environ["DB_PWD"],
            'HOST': os.environ.get("DB_HOST", '127.0.0.1'),
            'PORT': os.environ.get("DB_PORT", '5432'),
        }
    }

# https://docs.djangoproject.com/en/3.2/releases/3.2/#customizing-type-of-auto-created-primary-keys
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = os.environ.get('LANGUAGE_CODE', "en-us")
#LANGUAGES = os.environ.get('LANGUAGES', ('en', 'English'))
LANGUAGES = [('en', 'English'),]

#TIME_ZONE = 'UTC'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# for docker deployment:
# see https://stackoverflow.com/questions/52004910/django-and-docker-outputting-information-to-console/52010919
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[DJANGO] %(levelname)s %(asctime)s %(module)s '
            '%(name)s.%(funcName)s:%(lineno)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        }
    },
    'loggers': {
        'mybookdb': {
            'handlers': ['console'],
            'level': os.getenv('LOGLEVEL', 'DEBUG'),
            'propagate': False,
        },
        'django.utils.autoreload': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': os.getenv('LOGLEVEL_DJANGO', 'DEBUG'),
            'propagate': False,
        },
        '*': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}



# Redirect to home URL after login (Default redirects to /accounts/profile/)
LOGIN_REDIRECT_URL = '/'

# to test email:
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'



# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'


BOOTSTRAP4 = {
    'css_url': STATIC_URL +'js/lib/bootstrap/dist/css/bootstrap.css',
    'jquery_url': STATIC_URL +'js/lib/jquery/dist/jquery.js',
    'javascript_url': STATIC_URL +'js/lib/bootstrap/dist/js/bootstrap.js',
    'use_i18n': False,
    'popper_url': STATIC_URL +'js/lib/@popperjs/core/dist/umd/popper.min.js',
    
    # not available (yet) but overridden to prevent inclusion of external resources
    'jquery_slim_url': STATIC_URL +'js/lib/jquery/dist/jquery.slim.js',
}

STATIC_ROOT = os.path.join(BASE_DIR, 'static') 
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'templates', 'static'),
]

MEDIA_URL = "/media/"

MEDIA_ROOT = os.path.join(BASE_DIR, 'templates', 'media')

GRAPHENE = {
    'SCHEMA': 'mybookdb.schema.schema'
}
if DEBUG:
    GRAPHENE['MIDDLEWARE'] = (
        'graphene_django.debug.DjangoDebugMiddleware',
    )

GRAPHIQL_DEFAULT_QUERY = """
{
  users {
    id
    username
    lastLogin
    email
    #isStaff
    #isActive
    #dateJoined
  }
}
"""

INTERNAL_IPS = [  # for debug_toolbar
    '127.0.0.1',
]


DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'de')  # default book language

assert TEMPLATES[0]['BACKEND'] == 'django.template.backends.django.DjangoTemplates'
TEMPLATES[0]['OPTIONS']['context_processors'].append('mybookdb.context_processors.export_vars')

ONLEIHE_URL = os.environ.get("ONLEIHE_URL")
ONLEIHE_START = os.environ.get("ONLEIHE_START")
ONLEIHE_SEARCH = os.environ.get("ONLEIHE_SEARCH")
