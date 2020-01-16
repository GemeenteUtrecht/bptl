"""
Manage a registry of tasks that can be used as callbacks.

A Task is a callable which takes a
:class:`camunda_worker.external_tasks.models.FetchedTask` instance as sole argument and
performs a unit of work.
"""
from django.utils.module_loading import autodiscover_modules


class TaskRegistry:
    def __init__(self):
        self._registry = {}

    def autodiscover(self):
        autodiscover_modules("tasks", register_to=self)


# Sentinel to hold all tasks
register = TaskRegistry()
