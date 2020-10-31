# Insta Follow

##.env file

```python

DEBUG = True
DEVEL = True

ALLOWED_HOSTS = 'localhost, 127.0.0.1'


DB_ENGINE = 'django.db.backends.postgresql_psycopg2'
DB_NAME = ''
DB_USER = ''
DB_PASS = ''
DB_HOST = 'localhost'
DB_PORT = '5432'


CACHE_BACKEND = 'django.core.cache.backends.memcached.MemcachedCache'
CACHE_HOST = 'localhost:11211'

CELERY_USER = ''
CELERY_PASS = ''
CELERY_HOST = 'localhost'

TELEGRAM_BOT_TOKEN = ''
TELEGRAM_BOT_MODE = 'WEBHOOK'
TELEGRAM_BOT_WEBHOOK_SITE = 'https://twh.jobisms.com:8443'


```