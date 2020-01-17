from django.template import Library

from ..models import TaskMapping
from ..registry import Task, register as task_registry

register = Library()


@register.simple_tag
def get_registry_task(task_mapping: TaskMapping) -> Task:
    task = task_registry[task_mapping.callback]
    return task
