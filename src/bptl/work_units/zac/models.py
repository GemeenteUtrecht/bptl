from typing import Dict, Union

from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel


class ZACConfig(SingletonModel):
    api_root = models.URLField(
        _("API-root"),
        help_text=_("Root URL of ZAC api"),
        default="https://zac.example.com",
    )

    header_key = models.CharField(
        _("header key"),
        max_length=100,
        blank=True,
        help_text=_("HTTP Authorization header name, required if the API is not open."),
    )
    header_value = models.CharField(
        _("header value"),
        max_length=255,
        blank=True,
        help_text=_(
            "HTTP Authorization header value, required if the API is not open."
        ),
    )

    class Meta:
        verbose_name = _("Zac Configuration")

    def __str__(self):
        return self.api_root

    @property
    def auth_header(self) -> Union[Dict[str, str], None]:
        if self.header_key and self.header_value:
            return {self.header_key: self.header_value}

        return {}
