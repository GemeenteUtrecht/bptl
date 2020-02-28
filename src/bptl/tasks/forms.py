from typing import Tuple

from django import forms
from django.contrib.admin.widgets import AdminRadioSelect
from django.utils.html import format_html

from .models import TaskMapping
from .registry import register


def get_callback_choices() -> Tuple[Tuple[str, str]]:
    for task in register:
        task_label = format_html(
            '<span class="task-name">{name}</span>'
            "<br>"
            '<span class="task-doc">{doc}</span>',
            name=task.name,
            doc=task.html_documentation,
        )
        yield (task.dotted_path, task_label)


class CallbackField(forms.ChoiceField):
    def __init__(self, *args, **kwargs):
        self._max_length = kwargs.pop("max_length")
        kwargs.setdefault("choices", get_callback_choices)
        super().__init__(*args, **kwargs)


class AdminTaskMappingForm(forms.ModelForm):
    class Meta:
        model = TaskMapping
        fields = "__all__"
        field_classes = {"callback": CallbackField}
        widgets = {"callback": AdminRadioSelect}


class TaskMappingForm(forms.ModelForm):
    class Meta:
        model = TaskMapping
        fields = ("topic_name", "callback")
        field_classes = {"callback": CallbackField}
