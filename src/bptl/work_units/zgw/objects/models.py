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
