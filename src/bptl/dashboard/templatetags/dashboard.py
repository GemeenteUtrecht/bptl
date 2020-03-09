import json

from django.template import Library

from bptl.tasks.constants import ENGINETYPE_MODEL_MAPPING, EngineTypes
from bptl.utils.constants import Statuses

register = Library()


@register.filter
def task_type(task) -> str:
    for type, model in ENGINETYPE_MODEL_MAPPING.items():
        if isinstance(task, model):
            return EngineTypes.values[type]
    return ""


@register.filter
def pretty_json(value: str) -> str:
    return json.dumps(value, indent=4)


@register.filter
def display_status(value: str) -> str:
    return Statuses.values[value]
