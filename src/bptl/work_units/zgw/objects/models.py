from typing import List

from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel


class MetaObjectTypesConfig(SingletonModel):
    start_camunda_process_form_objecttype = models.URLField(
        _("URL-reference to StartCamundaForms in OBJECTTYPES API."),
        help_text=_(
            "A URL-reference to the StartCamundaForms OBJECTTYPE. This is used to set the right variables for the camunda process related to the ZAAKTYPE."
        ),
        default="",
    )
    checklisttype_objecttype = models.URLField(
        _("URL-reference to ChecklistType in OBJECTTYPES API."),
        help_text=_(
            "A URL-reference to the ChecklistType OBJECTTYPE. This is used to get the questions for a checklist for a ZAAKTYPE."
        ),
        default="",
    )
    checklist_objecttype = models.URLField(
        _("URL-reference to Checklist in OBJECTTYPES API."),
        help_text=_(
            "A URL-reference to the Checklist OBJECTTYPE. This is used to fetch the checklist objecttype for a ZAAK."
        ),
        default="",
    )

    class Meta:
        verbose_name = _("meta objecttype configuration")

    def __str__(self):
        return force_str(self._meta.verbose_name)

    @property
    def meta_objecttype_urls(self) -> List[str]:
        return [
            getattr(self, field.name)
            for field in self._meta.get_fields()
            if isinstance(field, models.URLField)
        ]
