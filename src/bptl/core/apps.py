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

        # Patch zgw-consumers Service model for backward compatibility
        from zgw_consumers.client import build_client as _build_client
        from zgw_consumers.models import Service

        from bptl.core.forms import PatchedPeriodicTaskForm
        from bptl.work_units.zgw.client import ZGWClient

        def build_client(self, **kwargs):
            """
            Build a ZGWClient for this Service.

            This method provides backward compatibility with zgw-consumers <1.0 by
            using our custom ZGWClient instead of the default NLXClient.

            The ZGWClient is a proper subclass of ape_pie.APIClient that adds:
            - API convenience methods (create, retrieve, list, etc.)
            - Logging via _log attribute
            - Full backward compatibility with the old ZGWClient API
            """
            # Use the official build_client function from zgw-consumers,
            # but specify our ZGWClient as the client_factory
            return _build_client(self, client_factory=ZGWClient, **kwargs)

        Service.build_client = build_client
