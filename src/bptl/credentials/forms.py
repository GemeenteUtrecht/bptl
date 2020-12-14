from typing import Any, Dict, List

from django import forms
from django.db.models import BLANK_CHOICE_DASH
from django.utils.translation import gettext_lazy as _

from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from bptl.work_units.zgw.utils import get_paginated_results

from .models import App


def _get_applications(service: Service) -> List[Dict[str, Any]]:
    client = service.build_client()
    results = get_paginated_results(client, "applicatie")
    return results


class AppForm(forms.ModelForm):
    autorisaties_application = forms.ChoiceField(
        label=_("Autorisaties API app"),
        required=False,
        help_text=_(
            "Application in Autorisaties API. If selected, label and App ID "
            "can be left blank."
        ),
    )

    class Meta:
        model = App
        fields = (
            "autorisaties_application",
            "label",
            "app_id",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._set_auth_api_choices()

    def _set_auth_api_choices(self):
        autorisatie_apis = Service.objects.filter(api_type=APITypes.ac)

        with parallel() as executor:
            applications = executor.map(_get_applications, autorisatie_apis)

        all_apps = sum(applications, [])
        all_apps = sorted(all_apps, key=lambda app: app["label"])

        # if there's no data, no point in showing the field at all
        if not all_apps:
            del self.fields["autorisaties_application"]
            return

        self.fields["autorisaties_application"].choices = BLANK_CHOICE_DASH + [
            (application["url"], application["label"]) for application in all_apps
        ]
        self.fields["label"].required = False
        self.fields["app_id"].required = False

        if self.instance.pk:
            self.fields["autorisaties_application"].initial = self.instance.app_id

    def clean(self):
        super().clean()

        app = self.cleaned_data.get("autorisaties_application")
        label = self.cleaned_data.get("label")
        app_id = self.cleaned_data.get("app_id")

        # if there's no application specified that we can derive the values from, the
        # other fields become required fields
        if not app:
            for field in ["label", "app_id"]:
                value = self.cleaned_data.get(field)
                if not value:
                    form_field = self.fields[field]
                    self.add_error(
                        field,
                        forms.ValidationError(
                            form_field.error_messages["required"], code="required"
                        ),
                    )

        else:
            ac_client = Service.get_client(app)
            application = ac_client.retrieve("applicatie", url=app)
            if not label:
                self.cleaned_data["label"] = application["label"]
            if not app_id:
                self.cleaned_data["app_id"] = application["url"]

        return self.cleaned_data
