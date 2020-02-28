from django.template import Library

from bptl.tasks.constants import ENGINETYPE_MODEL_MAPPING

register = Library()


@register.filter
def task_type(task) -> str:
    for type, model in ENGINETYPE_MODEL_MAPPING.items():
        if isinstance(task, model):
            return type
    return ""
