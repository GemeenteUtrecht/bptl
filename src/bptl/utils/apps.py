from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = "bptl.utils"

    def ready(self):
        from . import checks  # noqa
