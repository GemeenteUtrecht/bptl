from django.template import Library

from ..registry import Task, register as task_registry

register = Library()


@register.simple_tag
def get_registry_task(callback: str) -> Task:
    task = task_registry[callback]
    return task
