from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class CoreConfig(SingletonModel):
    non_sso_login_enabled = models.BooleanField(
        _("Non-SSO login enabled"),
        help_text=_("A flag that allows non-SSO login (True) or not (False)."),
        default=False,
    )
    primary_objecttypes_api = models.ForeignKey(
        verbose_name=_("Primary OBJECTTYPES API"),
        to="zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.orc},
        related_name="+",
        help_text=_("Default OBJECTTYPES API service to use"),
    )

    class Meta:
        verbose_name = _("global configuration")

    def __str__(self):
        return force_str(self._meta.verbose_name)
