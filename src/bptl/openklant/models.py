"""
Database models to keep track of "internal tasks" fetched from OpenKlant.

We save tasks in our own database in case of crashes and for dev purposes, so that we
can pick up work load again.
"""

from urllib.parse import urljoin

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, ugettext_lazy as _

from solo.models import SingletonModel
from zds_client.client import Client

from bptl.tasks.models import BaseTask
from bptl.tasks.utils import get_worker_id


class OpenKlantActorModel(SingletonModel):
    name = models.CharField(
        _("naam"),
        max_length=200,
        help_text=_("Required. 200 characters or fewer."),
        error_messages={
            "unique": _("An Actor with that name already exists."),
        },
    )
    uuid = models.UUIDField(
        _("Actor UUID"),
        help_text=_("UUID of the Actor associated with the BPTL within OpenKlant"),
        null=True,
        default=None,
    )

    class Meta:
        verbose_name = _("OpenKlant actor")

    def __str__(self):
        return f"{self.name} / {self.uuid}"


class OpenKlantConfig(SingletonModel):
    service = models.ForeignKey(
        "zgw_consumers.Service",
        on_delete=models.CASCADE,
        verbose_name=_("service"),
        help_text=_("External service to configure credentials for."),
        null=True,
    )
    objects_service = models.ForeignKey(
        "zgw_consumers.Service",
        on_delete=models.CASCADE,
        verbose_name=_("objects service"),
        help_text=_("External objects service used by OpenKlant."),
        null=True,
    )
    objecttypes_service = models.ForeignKey(
        "zgw_consumers.Service",
        on_delete=models.CASCADE,
        verbose_name=_("objecttypes service"),
        help_text=_("External objecttypes service used by OpenKlant."),
        null=True,
    )
    actor = models.ForeignKey(
        "OpenKlantActorModel",
        on_delete=models.CASCADE,
        verbose_name=_("OpenKlant Actor"),
        help_text=_("Actor associated with BPTL in OpenKlant."),
        null=True,
    )


class InterneTask(models.Model):
    gevraagde_handeling = models.CharField(
        max_length=200,
        default="",
        unique=True,
        help_text=_(
            "Gevraagde handeling voor actor(en) van interne taak in OpenKlant."
        ),
    )

    class Meta:
        verbose_name = _("Interne Tasks gevraagde handeling")

    def __str__(self):
        return self.gevraagde_handeling


class OpenKlantInternalTaskModel(BaseTask):
    """
    A single Open Klant internal task that was retrieved by the worker.

    We keep a number of fields to identify/match the tasks in the Open Klant component.

    """

    worker_id = models.CharField(
        default=get_worker_id,
        max_length=255,
        help_text=_(
            "The worker ID that picked up the task. Only the same "
            "worker ID is allowed to unlock/modify the task. Used as a lock."
        ),
    )
    task_id = models.CharField(_("task uuid"), max_length=50)
    openklant_error = models.JSONField(
        _("openklant error"),
        blank=True,
        null=True,
        default=None,
    )

    class Meta:
        verbose_name = _("openklant internal task")
        verbose_name_plural = _("openklant internal tasks")

    def __str__(self):
        return f"{self.topic_name} / {self.task_id}"
