from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    name = "bptl.core"
    verbose_name = _("business process task library")
