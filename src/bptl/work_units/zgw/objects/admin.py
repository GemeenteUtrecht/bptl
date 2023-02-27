from typing import List, Tuple

from django.contrib import admin
from django.forms import fields

from solo.admin import SingletonModelAdmin

from bptl.work_units.zgw.objects.models import MetaObjectTypesConfig


def get_objecttypes_choices() -> List[Tuple[str, str]]:
    from bptl.work_units.zgw.objects.services import fetch_objecttypes

    ots = fetch_objecttypes()
    return [(ot["url"], ot["name"]) for ot in ots]


@admin.register(MetaObjectTypesConfig)
class MetaObjectTypesConfigAdmin(SingletonModelAdmin):
    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        objecttype_fields = [
            "start_camunda_process_form_objecttype",
        ]
        for field in objecttype_fields:
            form.base_fields[field] = fields.ChoiceField(
                choices=get_objecttypes_choices(), required=False, initial=""
            )
        return form
