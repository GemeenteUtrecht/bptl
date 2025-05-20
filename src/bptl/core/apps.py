from django.apps import AppConfig
from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bptl.core"
    verbose_name = _("business process task library")

    def ready(self):
        # Delay the import until the app registry is ready
        from django_celery_beat.admin import PeriodicTaskForm

        # Dynamically patch the Meta class
        PeriodicTaskForm.Meta.fields = "__all__"

        from bptl.core.forms import PatchedPeriodicTaskForm
