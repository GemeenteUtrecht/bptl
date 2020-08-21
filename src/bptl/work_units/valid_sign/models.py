from django.db import models
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel


def get_auth_key():
    return get_random_string(length=50)


class ValidSignConfiguration(SingletonModel):
    auth_key = models.CharField(
        _("authentication key"),
        max_length=200,
        default=get_auth_key,
        help_text=_(
            "The unique authentication key for ValidSign. This maps to the 'key' "
            "field in the callback creation (https://apidocs.validsign.nl/#operation/api.callback.post). "
            "You should fill in this key when you configure the callback URL in the dashboard."
        ),
    )

    class Meta:
        verbose_name = _("ValidSign Configuration")

    def __str__(self):
        return force_text(self._meta.verbose_name)

    @property
    def callback_url(self):
        return reverse("valid_sign:callbacks")
