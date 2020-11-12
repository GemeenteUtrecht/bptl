from typing import Tuple

from django import forms
from django.contrib.admin.widgets import AdminRadioSelect
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.utils.html import format_html, mark_safe, urlize
from django.utils.translation import ugettext_lazy as _

from zgw_consumers.models import Service

from bptl.work_units.zgw.models import DefaultService

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


class ServiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return mark_safe(f"{obj.api_type}: {urlize(obj.api_root)}")


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


class DefaultServiceForm(forms.ModelForm):
    service = ServiceField(
        queryset=Service.objects,
        empty_label=None,
        label=_("Service"),
        help_text=_("ZGW Service to connect with"),
        widget=forms.RadioSelect,
    )

    class Meta:
        model = DefaultService
        fields = ("alias", "service")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["alias"].required = False


class BaseDefaultServiceFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()

        # selected callback - this is not validated because we don't have access to the
        # form.
        # TODO: check if django-extra-views CreateWithInlines has a proper solution for
        # this
        callback = self.data["callback"]
        if not callback:
            return  # won't validate the main form anyway

        try:
            task = register[self.data["callback"]]
        except KeyError:
            return  # won't validate the main form anyway

        import bpdb

        bpdb.set_trace()


DefaultServiceFormset = inlineformset_factory(
    TaskMapping,
    DefaultService,
    form=DefaultServiceForm,
    formset=BaseDefaultServiceFormset,
    extra=2,
)
