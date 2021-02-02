"""
Django settings for insta_follow project.

Generated by 'django-admin startproject' using Django 3.0.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""
import logging
from datetime import timedelta

from decouple import config, Csv
from pathlib import Path

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)
DEVEL = config("DEVEL", default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")
# This is used so that application data can hook into specific sites.
SITE_ID = 1
# Application definition
INSTALLED_APPS = [
    'apps.reward',
    'apps.contents',
    'apps.config',
    'apps.instagram_app',

    'rest_framework',
    'drf_yasg',
    # 'django_celery_beat',
    'tinymce',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.flatpages'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
]

ROOT_URLCONF = 'conf.urls'
APPEND_SLASH = False

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
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

WSGI_APPLICATION = 'conf.wsgi.application'
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'apps.instagram_app.utils.custom_exception_handler'
}
SIMPLE_JWT = {
    'ROTATE_REFRESH_TOKENS': True,
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('ACCESS_TOKEN_LIFETIME', default=56000, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=config('REFRESH_TOKEN_LIFETIME', default=90, cast=int)),
}

SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
    'SECURITY_DEFINITIONS': {
        'JWT': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
}

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASS'),
        'HOST': config('DB_HOST', default=""),
        'PORT': config('DB_PORT', default=""),
    },
}
# DATABASE_ROUTERS = ['apps.instagram_app.dbrouters.MongoRouter', ]

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators
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

CACHES = {
    'default': {
        'BACKEND': config('CACHE_BACKEND', default='django.core.cache.backends.locmem.LocMemCache'),
        'LOCATION': config('CACHE_HOST', default=''),
        'KEY_PREFIX': 'INSTA_FOLLOW',
    },

}

CELERY_BROKER_URL = 'amqp://%(USER)s:%(PASS)s@%(HOST)s' % {
    'USER': config('CELERY_USER'),
    'PASS': config('CELERY_PASS'),
    'HOST': config('CELERY_HOST'),
}

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/
LANGUAGE_CODE = config('LANGUAGE_CODE', default='en')
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_L10N = False
USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
STATIC_ROOT = BASE_DIR / 'static'
STATIC_URL = '/static/'

MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

FIXTURE_DIRS = [
    BASE_DIR / 'fixtures',
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

LOG_DIR = BASE_DIR / 'logs'
LOGGING = ({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[%(asctime)s] %(levelname)s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'verbose' if DEBUG else 'simple',
            'filename': LOG_DIR / 'django.log',
        },
        'db_queries': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'db_queries.log',
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['db_queries'],
            'propagate': False,
        },
        'apps.instagram_app': {
            'level': 'DEBUG',
            'handlers': ['file', 'console']
        },
        'apps.reward': {
            'level': 'DEBUG',
            'handlers': ['file', 'console']
        },

    },
})

INSTAGRAM_CREDENTIALS = {
    'USERNAME': config('INSTAGRAM_USERNAME', default=''),
    'PASSWORD': config('INSTAGRAM_PASSWORD', default=''),
}

DEVLYTIC_TOKEN = config('DEVLYTIC_TOKEN', default='')
PUSH_API_URL = config('PUSH_API_URL', default='')
PAYMENT_API_URL = config('PAYMENT_API_URL', default='')
PAYMENT_SERVICE_SECRET = config('PAYMENT_SERVICE_SECRET', default='')
MONITOR_TOKEN = config('MONITOR_TOKEN', default='')
USER_PENALTY_AMOUNT = config('USER_PENALTY_AMOUNT', default=2, cast=int)
PENALTY_CHECK_HOUR = config('PENALTY_CHECK_HOUR', default=48, cast=int)

ORDER_TARGET_RATIO = config('ORDER_TARGET_RATIO', default=100, cast=int)

FOLLOWER_LIMIT = config('FOLLOWER_LIMIT', default=1000, cast=int)
MAXIMUM_COIN_TRANSFER = config('MAXIMUM_COIN_TRANSFER', default=1000, cast=int)
DAILY_TRANSFER_LIMIT = config('DAILY_TRANSFER_LIMIT', default=2, cast=int)
COIN_TRANSFER_FEE = config('COIN_TRANSFER_FEE', default=5, cast=int)

TINYMCE_COMPRESSOR = config('TINYMCE_COMPRESSOR', default=False, cast=bool)
TINYMCE_DEFAULT_CONFIG = {
    "height": "320px",
    "width": "960px",
    "menubar": "file edit view insert format tools table help",
    "plugins": "advlist autolink lists link image charmap print preview anchor searchreplace visualblocks code "
               "fullscreen insertdatetime media table paste code help wordcount spellchecker",
    "toolbar": "undo redo | bold italic underline strikethrough | fontselect fontsizeselect formatselect | alignleft "
               "aligncenter alignright alignjustify | outdent indent |  numlist bullist checklist | forecolor "
               "backcolor casechange permanentpen formatpainter removeformat | pagebreak | charmap emoticons | "
               "fullscreen  preview save print | insertfile image media pageembed template link anchor codesample | "
               "a11ycheck ltr rtl | showcomments addcomment code",
    "custom_undo_redo_levels": 10,
    "language": "fa",  # To force a specific language instead of the Django current language.
}

CAFE_BAZAAR_PACKAGE_NAME = config('CAFE_BAZAAR_PACKAGE_NAME')
COIN_DAILY_REWARD_AMOUNT = config('COIN_DAILY_REWARD_AMOUNT', default=10, cast=int)

COIN_AD_VIEW_REWARD_AMOUNT = config('COIN_AD_VIEW_REWARD_AMOUNT', default=2, cast=int)
COIN_AD_CLICKED_REWARD_AMOUNT = config('COIN_AD_CLICKED_REWARD_AMOUNT', default=5, cast=int)
AD_CACHE_EXPIRY = config('AD_CACHE_EXPIRY', default=120, cast=int)

if DEVEL is False:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    SENTRY_KEY = config('SENTRY_KEY')
    SENTRY_HOST = config('SENTRY_HOST')
    SENTRY_PROJECT_ID = config('SENTRY_PROJECT_ID')
    SENTRY_ENV = config('SENTRY_ENV')

    sentry_sdk.init(
        dsn=f"https://{SENTRY_KEY}@{SENTRY_HOST}/{SENTRY_PROJECT_ID}",
        integrations=[DjangoIntegration(), CeleryIntegration(), LoggingIntegration(event_level=logging.CRITICAL)],
        default_integrations=False,

        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,

        # Custom settings
        debug=DEBUG,
        environment=SENTRY_ENV
    )
