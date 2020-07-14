import os
import warnings

os.environ.setdefault(
    "SECRET_KEY", "8n47ma!3%cfdm3cgt)@1ozjo7+^!j+z18@+0f-2+!p6ba^kof_"
)
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1")

# uses postgresql by default, see base.py
os.environ.setdefault("DB_NAME", "bptl"),
os.environ.setdefault("DB_USER", "bptl"),
os.environ.setdefault("DB_PASSWORD", "bptl"),

from .base import *  # noqa isort:skip

# Feel free to switch dev to sqlite3 for simple projects,
# or override DATABASES in your local.py
# DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'

#
# Standard Django settings.
#

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

ADMINS = ()
MANAGERS = ADMINS

LOGGING["loggers"].update(
    {
        "bptl": {"handlers": ["console"], "level": "DEBUG", "propagate": True,},
        "django": {"handlers": ["console"], "level": "DEBUG", "propagate": True,},
        "django.db.backends": {
            "handlers": ["django"],
            "level": "DEBUG",
            "propagate": False,
        },
        "performance": {"handlers": ["console"], "level": "INFO", "propagate": True,},
        #
        # See: https://code.djangoproject.com/ticket/30554
        # Autoreload logs excessively, turn it down a bit.
        #
        "django.utils.autoreload": {
            "handlers": ["django"],
            "level": "INFO",
            "propagate": False,
        },
    }
)

#
# Additional Django settings
#

# Disable security measures for development
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = False

#
# Custom settings
#
ENVIRONMENT = "development"

#
# Library settings
#

ELASTIC_APM["DEBUG"] = True

# Django debug toolbar
INSTALLED_APPS += [
    "debug_toolbar",
    "django_extensions",
]
MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]
INTERNAL_IPS = ("127.0.0.1",)
DEBUG_TOOLBAR_CONFIG = {"INTERCEPT_REDIRECTS": False}

AXES_BEHIND_REVERSE_PROXY = (
    False  # Default: False (we are typically using Nginx as reverse proxy)
)

# in memory cache and django-axes don't get along.
# https://django-axes.readthedocs.io/en/latest/configuration.html#known-configuration-problems
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache",},
    "axes_cache": {"BACKEND": "django.core.cache.backends.dummy.DummyCache",},
}

AXES_CACHE = "axes_cache"


REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += (
    "rest_framework.renderers.BrowsableAPIRenderer",
)
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] += (
    "rest_framework.authentication.SessionAuthentication",
)

# THOU SHALT NOT USE NAIVE DATETIMES
warnings.filterwarnings(
    "error",
    r"DateTimeField .* received a naive datetime",
    RuntimeWarning,
    r"django\.db\.models\.fields",
)

# ValidSign settings
VALIDSIGN_ROOT_URL = os.environ.setdefault(
    "VALIDSIGN_ROOT_URL", "https://try.validsign.nl/"
)

# Override settings with local settings.
try:
    from .local import *  # noqa
except ImportError:
    pass
