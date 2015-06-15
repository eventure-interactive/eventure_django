"""
Django settings for evtidj project.

Generated by 'django-admin startproject' using Django 1.8.

Intended for production use
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import socket
from six.moves.urllib.parse import quote
from kombu import Exchange, Queue

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '+&6-94v)i$^^ssu*cngktky$i3kxwfe=f&d(6ak8cjI&t!8y)ig*oak(c_5sfs'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ["devapi-rest.eventure.com"]
CONN_MAX_AGE = 600

AUTH_USER_MODEL = 'core.Account'

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djcelery',
    # 'debug_toolbar',

    'rest_framework',
    'core',

    'django.contrib.gis',
)

MIDDLEWARE_CLASSES = (
    # 'evtidj.disable.DisableCSRF',  # Disable to allow for load testing, take out for 'real' prod
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'evtidj.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'evtidj.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'evti',
        'USER': 'web-dev',
        'PASSWORD': '1Billion',
        'HOST': 'pgdb-dev.eventure.com',
        'PORT': 5432,
    }
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = '/home/ubuntu/static/'

REST_FRAMEWORK = {
    'PAGE_SIZE': 25,
}

# These credentials are for the eventure-mediaserver-dev account
AWS_MEDIA_ACCESS_KEY = 'AKIAIUIZFAO5NV43556Q'
AWS_MEDIA_SECRET_KEY = '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'
S3_MEDIA_UPLOAD_BUCKET = 'evtimedia'
S3_MEDIA_KEY_PREFIX = 'dev/'
S3_MEDIA_REGION = 'us-east-1'


CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json', 'yaml']
CELERY_RESULT_SERIALIZER = 'json'

CELERY_ENABLE_REMOTE_CONTROL = False
CELERY_SEND_EVENTS = False

CELERY_ENABLE_UTC = True
CELERY_DISABLE_RATE_LIMITS = True
BROKER_URL = 'sqs://{}:{}@'.format(AWS_MEDIA_ACCESS_KEY, quote(AWS_MEDIA_SECRET_KEY, safe=''))
BROKER_TRANSPORT_OPTIONS = {
    'queue_name_prefix': 'dev-',
    'visibility_timeout': 60,  # seconds
    'wait_time_seconds': 20,   # Long-polling
}


TEMP_ALBUMFILE_DIR = os.path.join(BASE_DIR, 'albumfile_tmp')
HOST_NAME = socket.gethostname()
