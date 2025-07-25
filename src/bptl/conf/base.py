import os

# Django-hijack (and Django-hijack-admin)
from django.urls import reverse_lazy

from celery.schedules import crontab, schedule
from sentry_sdk.integrations import django, redis

try:
    from sentry_sdk.integrations import celery
except ImportError:  # no celery in this proejct
    celery = None

from .environ import config

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
DJANGO_PROJECT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.path.pardir)
)
BASE_DIR = os.path.abspath(
    os.path.join(DJANGO_PROJECT_DIR, os.path.pardir, os.path.pardir)
)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

SITE_ID = config("SITE_ID", default=1)
IS_HTTPS = config("IS_HTTPS", default=not DEBUG)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "bptl"),
        "USER": os.getenv("DB_USER", "bptl"),
        "PASSWORD": os.getenv("DB_PASSWORD", "bptl"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", 5432),
    }
}

# Application definition

INSTALLED_APPS = [
    # Note: contenttypes should be first, see Django ticket #10827
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    # Note: If enabled, at least one Site object is required
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    "ordered_model",
    "django_admin_index",
    # Optional applications.
    "django.contrib.admin",
    # 'django.contrib.admindocs',
    "django.contrib.humanize",
    # 'django.contrib.sitemaps',
    # External applications.
    "axes",
    "django_auth_adfs",
    "django_auth_adfs_db",
    "sniplates",
    "hijack",
    "compat",  # Part of hijack
    "hijack_admin",
    "solo",
    "django_camunda",
    "django_filters",
    "drf_yasg",
    "polymorphic",
    "rest_framework",
    "rest_framework.authtoken",
    "timeline_logger",
    "zgw_consumers",
    "django_celery_beat",
    # Project applications.
    "bptl.accounts",
    "bptl.activiti",
    "bptl.camunda",
    "bptl.openklant",
    "bptl.core",
    "bptl.credentials",
    "bptl.dashboard",
    "bptl.tasks",
    "bptl.dummy",
    "bptl.utils",
    "bptl.work_units.brp",
    "bptl.work_units.camunda_api",
    "bptl.work_units.kadaster",
    "bptl.work_units.kownsl",
    "bptl.work_units.zgw",
    "bptl.work_units.zgw.objects",
    "bptl.work_units.zgw.zac",
    "bptl.work_units.valid_sign",
    "bptl.work_units.mail",
    "bptl.work_units.xential",
    "bptl.work_units.open_klant",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "bptl.urls"

# List of callables that know how to import templates from various sources.
RAW_TEMPLATE_LOADERS = (
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
    # 'admin_tools.template_loaders.Loader',
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(DJANGO_PROJECT_DIR, "templates"),
        ],
        "APP_DIRS": False,  # conflicts with explicity specifying the loaders
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "bptl.utils.context_processors.settings",
                # REQUIRED FOR ADMIN INDEX
                "django_admin_index.context_processors.dashboard",
            ],
            "loaders": RAW_TEMPLATE_LOADERS,
        },
    },
]

WSGI_APPLICATION = "bptl.wsgi.application"

# Database: Defined in target specific settings files.
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

SESSION_COOKIE_NAME = "bptl_sessionid"

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "nl-nl"

TIME_ZONE = "Europe/Amsterdam"

USE_I18N = True

USE_L10N = True

USE_TZ = True

USE_THOUSAND_SEPARATOR = True

# Translations
LOCALE_PATHS = (os.path.join(DJANGO_PROJECT_DIR, "conf", "locale"),)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = "/static/"

STATIC_ROOT = os.path.join(BASE_DIR, "static")

# Additional locations of static files
STATICFILES_DIRS = (os.path.join(DJANGO_PROJECT_DIR, "static"),)

# List of finder classes that know how to find static files in
# various locations

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"
FILE_UPLOAD_PERMISSIONS = 0o644

FIXTURE_DIRS = (os.path.join(DJANGO_PROJECT_DIR, "fixtures"),)

#
# Sending EMAIL
#
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
# disabled on Google Cloud, use 487 instead
EMAIL_PORT = config("EMAIL_PORT", default=25)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False)
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="bptl@example.com")

LOG_STDOUT = config("LOG_STDOUT", default=False)

LOGGING_DIR = os.path.join(BASE_DIR, "log")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(process)d %(thread)d  %(message)s"
        },
        "timestamped": {"format": "%(asctime)s %(levelname)s %(name)s  %(message)s"},
        "simple": {"format": "%(levelname)s  %(message)s"},
        "performance": {
            "format": "%(asctime)s %(process)d | %(thread)d | %(message)s",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "null": {
            "level": "DEBUG",
            "class": "logging.NullHandler",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "timestamped",
        },
        "django": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "django.log"),
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "project": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "bptl.log"),
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "performance": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "performance.log"),
            "formatter": "performance",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
    },
    "loggers": {
        "bptl": {
            "handlers": ["project"] if not LOG_STDOUT else ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["project"] if not LOG_STDOUT else ["console"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.template": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

#
# Additional Django settings
#

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Custom user model
AUTH_USER_MODEL = "accounts.User"

# Allow logging in with both username+password and email+password
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django_auth_adfs_db.backends.AdfsAuthCodeBackend",
    "bptl.accounts.backends.UserModelEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = reverse_lazy("admin:login")
LOGIN_REDIRECT_URL = reverse_lazy("index")

#
# Custom settings
#
PROJECT_NAME = "bptl"
ENVIRONMENT = None
SHOW_ALERT = True

#
# Library settings
#


# Django-Admin-Index
ADMIN_INDEX_SHOW_REMAINING_APPS = True
ADMIN_INDEX_AUTO_CREATE_APP_GROUP = True

# Django-Axes (4.0+)
#
# The number of login attempts allowed before a record is created for the
# failed logins. Default: 3
AXES_FAILURE_LIMIT = 10
# If set, defines a period of inactivity after which old failed login attempts
# will be forgotten. Can be set to a python timedelta object or an integer. If
# an integer, will be interpreted as a number of hours. Default: None
AXES_COOLOFF_TIME = 1
# If True only locks based on user id and never locks by IP if attempts limit
# exceed, otherwise utilize the existing IP and user locking logic Default:
# False
AXES_ONLY_USER_FAILURES = True
# If set, specifies a template to render when a user is locked out. Template
# receives cooloff_time and failure_limit as context variables. Default: None
AXES_LOCKOUT_TEMPLATE = "account_blocked.html"
AXES_USE_USER_AGENT = True  # Default: False
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True  # Default: False

# The default meta precedence order
IPWARE_META_PRECEDENCE_ORDER = (
    "HTTP_X_FORWARDED_FOR",
    "X_FORWARDED_FOR",  # <client>, <proxy1>, <proxy2>
    "HTTP_CLIENT_IP",
    "HTTP_X_REAL_IP",
    "HTTP_X_FORWARDED",
    "HTTP_X_CLUSTER_CLIENT_IP",
    "HTTP_FORWARDED_FOR",
    "HTTP_FORWARDED",
    "HTTP_VIA",
    "REMOTE_ADDR",
)

# Django-Hijack
HIJACK_LOGIN_REDIRECT_URL = "/"
HIJACK_LOGOUT_REDIRECT_URL = reverse_lazy("admin:accounts_user_changelist")
# The Admin mixin is used because we use a custom User-model.
HIJACK_REGISTER_ADMIN = False
# This is a CSRF-security risk.
# See: http://django-hijack.readthedocs.io/en/latest/configuration/#allowing-get-method-for-hijack-views
HIJACK_ALLOW_GET_REQUESTS = True

#
# AUTH-ADFS
#
AUTH_ADFS = {"SETTINGS_CLASS": "django_auth_adfs_db.settings.Settings"}

# Sentry SDK
SENTRY_DSN = os.getenv("SENTRY_DSN")

SENTRY_SDK_INTEGRATIONS = [
    django.DjangoIntegration(),
    redis.RedisIntegration(),
]
if celery is not None:
    SENTRY_SDK_INTEGRATIONS.append(celery.CeleryIntegration())

if SENTRY_DSN:
    import sentry_sdk

    SENTRY_CONFIG = {
        "dsn": SENTRY_DSN,
        "release": os.getenv("VERSION_TAG", "VERSION_TAG not set"),
    }

    sentry_sdk.init(
        **SENTRY_CONFIG, integrations=SENTRY_SDK_INTEGRATIONS, send_default_pii=True
    )

# Elastic APM

ELASTIC_APM = {
    "SERVICE_NAME": "bptl",
    "SECRET_TOKEN": os.getenv("ELASTIC_APM_SECRET_TOKEN", "default"),
    "SERVER_URL": os.getenv("ELASTIC_APM_SERVER_URL", "http://example.com"),
}

# Celery
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Add a 30 minutes timeout to all Celery tasks.
CELERY_TASK_SOFT_TIME_LIMIT = int(
    os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", default=30 * 60)
)  # 30 minutes
CELERY_QUEUE_ONCE_TIMEOUT = os.getenv(
    "CELERY_QUEUE_ONCE_TIMEOUT", CELERY_TASK_SOFT_TIME_LIMIT
)

# Setup Celery routes for long-polling
CELERY_TASK_ROUTES = {
    "bptl.camunda.tasks.task_fetch_and_lock": {"queue": "long-polling"},
    "bptl.openklant.tasks.task_fetch_and_patch": {"queue": "klantcontact"},
    "bptl.openklant.tasks.task_schedule_new_fetch_and_patch": {"queue": "klantcontact"},
}

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# CELERY_BEAT_SCHEDULE = {
#     "task-pull": {
#         "task": "bptl.camunda.tasks.task_fetch_and_lock",
#         # run every 10 seconds - we leave this, even though the long-poll timeout is set
#         # to 10 minutes (see LONG_POLLING_TIMEOUT_MINUTES). This ensures that beat will
#         # start the polling after 10 seconds, and keep it running. The task itself
#         # is marked graceful, so it'll just return None and not be scheduled again.
#         "schedule": schedule(run_every=10),
#     },
#     "interne-taak-pull": {
#         "task": "bptl.openklant.tasks.task_fetch_and_patch",
#         "schedule": schedule(run_every=30),
#     },
#     "retry-failed-tasks": {
#         "task": "bptl.openklant.tasks.task_schedule_new_fetch_and_patch",
#         "schedule": crontab(hour=18, minute=0),  # Runs every day at 18:00 UTC
#     },
# }

CELERY_TASK_ACKS_LATE = True
# ensure that no tasks are scheduled to a worker that may be running a long-poll
# TODO: use different queues for long-poll workers
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_ONCE = {
    "backend": "celery_once.backends.Redis",
    "settings": {
        "url": os.getenv("CELERY_ONCE_REDIS_URL", CELERY_BROKER_URL),
        "default_timeout": 60 * 60,  # one hour
    },
}

# project application settings
MAX_TASKS = 10
ZGW_CONSUMERS_CLIENT_CLASS = "bptl.work_units.zgw.client.ZGWClient"
ZGW_CONSUMERS_TEST_SCHEMA_DIRS = [
    os.path.join(DJANGO_PROJECT_DIR, "work_units", "zgw", "tests", "schemas"),
]


LONG_POLLING_TIMEOUT_MINUTES = config("LONG_POLLING_TIMEOUT_MINUTES", default=10)

# api settings
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    # Versioning
    "DEFAULT_VERSION": "1",  # NOT to be confused with API_VERSION - it's the major version part
    "ALLOWED_VERSIONS": ("1",),
    "VERSION_PARAM": "version",
    # test
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# OAS settings
SWAGGER_SETTINGS = {
    # Use apiKey type since OAS2 doesn't support Bearer authentication
    "SECURITY_DEFINITIONS": {
        "Token": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
}

# ValidSign Documents settings
# The maximum size (in bytes) that all the documents combined can have
MAX_TOTAL_DOCUMENT_SIZE = os.getenv("MAX_TOTAL_DOCUMENT_SIZE", 250000000)
# The maximum size (in bytes) that each document can have
MAX_DOCUMENT_SIZE = os.getenv("MAX_DOCUMENT_SIZE", 2621440)
# The size of the document chunks to load in memory
CHUNK_SIZE = os.getenv("CHUNK_SIZE", 4096)

# Xential ticket settings
XENTIAL_URL_TOKEN_TIMEOUT_DAYS = os.getenv("XENTIAL_URL_TOKEN_TIMEOUT_DAYS", default=7)

# KlantContact email settings
KCC_DEFAULT_FROM_EMAIL = os.getenv("KCC_DEFAULT_FROM_EMAIL", DEFAULT_FROM_EMAIL)
KCC_EMAIL_HOST = config("KCC_EMAIL_HOST", default=EMAIL_HOST)
KCC_EMAIL_PORT = config("KCC_EMAIL_PORT", default=EMAIL_PORT)
KCC_EMAIL_HOST_USER = config("KCC_EMAIL_HOST_USER", default=EMAIL_HOST_USER)
KCC_EMAIL_HOST_PASSWORD = config("KCC_EMAIL_HOST_PASSWORD", default=EMAIL_HOST_PASSWORD)
KCC_EMAIL_USE_TLS = config("KCC_EMAIL_USE_TLS", default=EMAIL_USE_TLS)
KCC_EMAIL_USE_SSL = config("KCC_EMAIL_USE_SSL", default=None)
KCC_EMAIL_TIMEOUT = config("KCC_EMAIL_TIMEOUT", default=EMAIL_TIMEOUT)
