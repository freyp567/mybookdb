"""
Django settings for mybookdb project.

Generated by 'django-admin startproject' using Django 2.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
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
    ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "127.0.0.1").split(',')
    #ALLOWED_HOSTS = ['*']
else:
    ALLOWED_CIDR_NETS = ALLOWED_CIDR_NETS.split(',')


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
    'django_prometheus',
]
if DEBUG:
    INSTALLED_APPS.append('debug_toolbar')
    

CRISPY_TEMPLATE_PACK = 'bootstrap4'

# 2018-10-23 dropped django_graphiql, seems to be deprecated and outdated
# and replaced completely by graphene_django
# use graphene-django to integrate GraphiQL into Django project

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allow_cidr.middleware.AllowCIDRMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

if DEBUG:
    # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#enabling-middleware
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'mybookdb.urls'
#ROOT_URLCONF = "graphite.urls_prometheus_wrapper" ?

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

DATABASES = {
    'default': {
        # 'ENGINE': 'django.db.backends.sqlite3',
        'ENGINE': 'django_prometheus.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.postgresql_psycopg2',
#        'NAME': 'mybookdb',
#        'USER': 'mybookdbusr',
#        'PASSWORD': os.environ["DB_PWD"],
#        'HOST': os.environ.get("DB_HOST", '127.0.0.1'),
#        'PORT': os.environ.get("DB_PORT", '5432'),
#    }
#}


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
LANGUAGES = os.environ.get('LANGUAGES', ('en', 'English'))

#TIME_ZONE = 'UTC'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'mybookdb': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': os.getenv('LOGLEVEL_DJANGO', 'DEBUG'),
            'propagate': True,
        }
    }
}

# Redirect to home URL after login (Default redirects to /accounts/profile/)
LOGIN_REDIRECT_URL = '/'

# to test email:
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'



# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'

#class StaticWrapper:


#BOOTSTRAP3 = {
#    'css_url': STATIC_URL +'bootstrap4/dist/css/bootstrap.min.css',
#    'jquery_url': STATIC_URL +'jquery/dist/jquery.min.js',
#    'javascript_url': STATIC_URL +'bootstrap/dist/js/bootstrap.min.js',
#}

BOOTSTRAP4 = {
    'css_url': STATIC_URL +'bootstrap4/dist/css/bootstrap.css',
    'jquery_url': STATIC_URL +'jquery/dist/jquery.js',
    #'javascript_url': STATIC_URL +'bootstrap/js/bootstrap.js',
    'javascript_url': STATIC_URL +'bootstrap4/dist/js/bootstrap.js',
    #'use_i18n': False,
    'popper_url': STATIC_URL +'popper.js/umd/popper.min.js',
    
    # not available (yet) but overridden to prevent inclusion of external resources
    'jquery_slim_url': STATIC_URL +'jquery/dist/jquery.slim.js',
}

#STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 
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


assert TEMPLATES[0]['BACKEND'] == 'django.template.backends.django.DjangoTemplates'
TEMPLATES[0]['OPTIONS']['context_processors'].append('mybookdb.context_processors.export_vars')

ONLEIHE_URL = os.environ.get("ONLEIHE_URL")
ONLEIHE_START = os.environ.get("ONLEIHE_START")
ONLEIHE_SEARCH = os.environ.get("ONLEIHE_SEARCH")
