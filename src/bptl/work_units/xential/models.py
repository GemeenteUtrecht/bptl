from django.db import models
from django.utils.translation import gettext_lazy as _


class XentialTicket(models.Model):
    """
    Store the relation between an executed task and a Xential ticket.
    """

    bptl_ticket_uuid = models.UUIDField(
        _("BPTL ticket UUID"),
        max_length=200,
        help_text=_("BPTL specific Xential ticket UUID"),
    )
    ticket_uuid = models.UUIDField(
        _("Xential ticket UUID"), max_length=200, help_text=_("Xential ticket UUID")
    )
    task = models.ForeignKey("tasks.BaseTask", on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("Xential Ticket")
        verbose_name_plural = _("Xential Tickets")

    def __str__(self):
        return self.bptl_ticket_uuid
