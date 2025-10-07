import sentry_sdk

from .base import *

#
# Standard Django settings.
#

DEBUG = False

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "bptl",
        "USER": "bptl",
        "PASSWORD": "bptl",
        "HOST": "",  # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        "PORT": "",  # Set to empty string for default.
        "CONN_MAX_AGE": 60,  # Lifetime of a database connection for performance.
    }
}

# Make this unique, and don't share it with anybody.
SECRET_KEY = "8n47ma!3%cfdm3cgt)@1ozjo7+^!j+z18@+0f-2+!p6ba^kof_"

ALLOWED_HOSTS = []

# Redis cache backend
# NOTE: If you do not use a cache backend, do not use a session backend or
# cached template loaders that rely on a backend.
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/2",  # NOTE: watch out for multiple projects using the same cache!
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
    "oidc": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/2",  # NOTE: watch out for multiple projects using the same cache!
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
}


# Caching sessions.
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Caching templates.
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    ("django.template.loaders.cached.Loader", RAW_TEMPLATE_LOADERS),
]

# The file storage engine to use when collecting static files with the
# collectstatic management command.
# Feel free to enable after checking with Sven
# STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Production logging facility.
LOGGING["loggers"].update(
    {
        "django": {
            "handlers": ["django"],
            "level": "INFO",
            "propagate": True,
        },
        "django.security.DisallowedHost": {
            "handlers": ["django"],
            "level": "CRITICAL",
            "propagate": False,
        },
    }
)

#
# Custom settings
#

# Show active environment in admin.
ENVIRONMENT = "production"
SHOW_ALERT = False

# We will assume we're running under https
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True

# SAMEORIGIN by default. Enable the following if no iframes are used
# X_FRAME_OPTIONS = 'DENY'

# Only set this when we're behind Nginx as configured in our example-deployment
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True  # Sets X-Content-Type-Options: nosniff
SECURE_BROWSER_XSS_FILTER = True  # Sets X-XSS-Protection: 1; mode=block

#
# Library settings
#

ELASTIC_APM["SERVICE_NAME"] += " " + ENVIRONMENT

# Sentry SDK
SENTRY_CONFIG = {
    "dsn": "https://",
    "public_dsn": "https://",
    "release": os.getenv("VERSION_TAG", "VERSION_TAG not set"),
}

sentry_sdk.init(
    dsn=SENTRY_CONFIG["dsn"],
    release=SENTRY_CONFIG["release"],
    integrations=SENTRY_SDK_INTEGRATIONS,
    send_default_pii=True,
)

# APM
MIDDLEWARE = ["elasticapm.contrib.django.middleware.TracingMiddleware"] + MIDDLEWARE
INSTALLED_APPS = INSTALLED_APPS + [
    "elasticapm.contrib.django",
]
