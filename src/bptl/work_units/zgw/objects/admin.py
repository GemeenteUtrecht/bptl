from typing import List, Tuple

from django.contrib import admin
from django.forms import fields

from solo.admin import SingletonModelAdmin

from bptl.core.models import CoreConfig
from bptl.work_units.zgw.objects.models import MetaObjectTypesConfig


def get_objecttypes_choices() -> List[Tuple[str, str]]:
    config = CoreConfig.get_solo()
    service = config.primary_objecttypes_api
    client = service.build_client()
    response = client.list("objecttype")
    return [(ot["url"], ot["name"]) for ot in response]


@admin.register(MetaObjectTypesConfig)
class MetaObjectTypesConfigAdmin(SingletonModelAdmin):
    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        objecttype_fields = [
            "zaaktype_attribute_objecttype",
            "start_camunda_process_form_objecttype",
            "oudbehandelaren_objecttype",
            "checklisttype_objecttype",
            "checklist_objecttype",
            "meta_list_objecttype",
        ]
        for field in objecttype_fields:
            form.base_fields[field] = fields.ChoiceField(
                choices=get_objecttypes_choices(), required=False, initial=""
            )
        return form
