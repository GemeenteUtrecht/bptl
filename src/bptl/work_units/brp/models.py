from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class BRPConfig(SingletonModel):
    service = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.orc},
        verbose_name=_("service"),
        help_text=_("Configurations for the client that makes requests to the API."),
    )

    class Meta:
        verbose_name = _("BRP Configuration")

    def __str__(self):
        return self.service.api_root
