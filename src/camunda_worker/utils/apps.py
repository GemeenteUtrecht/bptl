from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = "camunda_worker.utils"

    def ready(self):
        from . import checks  # noqa
