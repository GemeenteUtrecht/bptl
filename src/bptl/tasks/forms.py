from typing import Tuple

from django import forms
from django.contrib.admin.widgets import AdminRadioSelect
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.utils.html import format_html, mark_safe, urlize
from django.utils.translation import ugettext_lazy as _

from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from .models import DefaultService, TaskMapping
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
            task = register[callback]
        except KeyError:
            return  # won't validate the main form anyway

        if not hasattr(self, "cleaned_data"):
            return  # validation didn't run yet

        _pinned_alias_services = []
        # first round validates all the explicitly expected aliases
        for required_service in task.required_services:
            # if a particular alias is required, validate it as such
            alias = required_service.alias
            if not alias:
                continue
            # check that the alias is present
            service_data = next(
                (data for data in self.cleaned_data if data.get("alias") == alias),
                None,
            )

            if service_data is None:
                raise forms.ValidationError(
                    _("Missing service alias '{alias}'").format(alias=alias)
                )

            _pinned_alias_services.append(service_data)

            # check that the service is of the right type
            api_type = service_data["service"].api_type
            if api_type != required_service.service_type:
                index = self.cleaned_data.index(service_data)
                form = self.forms[index]
                form.add_error(
                    "service",
                    _(
                        "The service for alias '{alias}' must be a '{api_type}' service."
                    ).format(
                        alias=alias,
                        api_type=APITypes.labels[required_service.service_type],
                    ),
                )

        # if any form errors are introduced, the formset is no longer valid and has no
        # cleaned_data anymore -> so bypass the remaining validation
        if not self.is_valid():
            return

        # second round validates the free aliases
        candidates = [
            form_data
            for form_data in self.cleaned_data
            if form_data not in _pinned_alias_services and form_data.get("service")
        ]
        for required_service in task.required_services:
            if required_service.alias:
                continue

            has_candidate = any(
                candidate["service"].api_type == required_service.service_type
                for candidate in candidates
            )
            if not has_candidate:
                raise forms.ValidationError(
                    _(
                        "Missing a service of type '{api_type}' which is required for this task."
                    ).format(
                        api_type=APITypes.labels[required_service.service_type],
                    )
                )


DefaultServiceFormset = inlineformset_factory(
    TaskMapping,
    DefaultService,
    form=DefaultServiceForm,
    formset=BaseDefaultServiceFormset,
    extra=2,
)
