from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class CoreConfig(SingletonModel):
    non_adfs_login_enabled = models.BooleanField(
        _("Non-ADFS login enabled"),
        help_text=_("A flag that allows non-ADFS login (True) or not (False)."),
        default=False,
    )

    class Meta:
        verbose_name = _("global configuration")

    def __str__(self):
        return force_str(self._meta.verbose_name)
