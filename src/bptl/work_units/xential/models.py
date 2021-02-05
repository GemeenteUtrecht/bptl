from django.db import models
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel


class XentialTicket(models.Model):
    """
    Store the relation between an executed task and a Xential ticket.
    """

    bptl_ticket_uuid = models.UUIDField(
        _("BPTL ticket UUID"),
        help_text=_("BPTL specific Xential ticket UUID"),
    )
    ticket_uuid = models.UUIDField(
        _("Xential ticket UUID"), help_text=_("Xential ticket UUID")
    )
    task = models.ForeignKey("tasks.BaseTask", on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("Xential Ticket")
        verbose_name_plural = _("Xential Tickets")

    def __str__(self):
        return str(self.bptl_ticket_uuid)


def get_auth_key():
    return get_random_string(length=50)


class XentialConfiguration(SingletonModel):
    auth_key = models.CharField(
        _("authentication key"),
        max_length=200,
        default=get_auth_key,
        help_text=_(
            "The unique authentication key for Xential API to authenticate itself when"
            "returning a newly built document."
        ),
    )

    class Meta:
        verbose_name = _("Xential Configuration")

    def __str__(self):
        return force_text(self._meta.verbose_name)

    @property
    def callback_url(self):
        return reverse("Xential:xential-callbacks")
