from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

from .registry import register


class TasksConfig(AppConfig):
    name = "bptl.tasks"
    verbose_name = _("Task configuration")

    def ready(self):
        register.autodiscover()
