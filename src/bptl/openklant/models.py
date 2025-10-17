"""
Database models to keep track of "internal tasks" fetched from OpenKlant.

We save tasks in our own database in case of crashes and for dev purposes, so that we
can pick up work load again.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel

from bptl.tasks.models import BaseTask
from bptl.tasks.utils import get_worker_id

from .constants import FailedTaskStatuses


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
        related_name="objects_service",
    )
    objecttypes_service = models.ForeignKey(
        "zgw_consumers.Service",
        on_delete=models.CASCADE,
        verbose_name=_("objecttypes service"),
        help_text=_("External objecttypes service used by OpenKlant."),
        null=True,
        related_name="objecttypes_service",
    )
    actor = models.ForeignKey(
        "OpenKlantActorModel",
        on_delete=models.CASCADE,
        verbose_name=_("OpenKlant Actor"),
        help_text=_("Actor associated with BPTL in OpenKlant."),
        null=True,
    )
    debug = models.BooleanField(
        _("debug mode"),
        default=False,
        help_text=_("Enable debug mode for OpenKlant tasks."),
    )
    debug_email = models.EmailField(
        _("debug email"),
        max_length=254,
        help_text=_("Email address for debugging emails in OpenKlant."),
        blank=True,
        null=True,
    )
    logging_email = models.EmailField(
        _("logging email"),
        max_length=254,
        help_text=_("Email address for logging emails in OpenKlant."),
        blank=True,
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


class FailedOpenKlantTasks(models.Model):
    task = models.OneToOneField(
        OpenKlantInternalTaskModel,
        on_delete=models.CASCADE,
        related_name="failed_task",
        help_text="The OpenKlantInternalTaskModel that failed.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text=_("When the task failed.")
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text=_("Last updated timestamp.")
    )
    reason = models.TextField(
        blank=True,
        null=True,
        help_text=_("The reason why the task failed, including the exception message."),
    )
    status = models.CharField(
        max_length=50,
        choices=FailedTaskStatuses.choices,
        default=FailedTaskStatuses.initial,
        help_text=_("The status of the failed task."),
    )

    def __str__(self):
        return f"Failed OpenKlant InternalTask: {self.task.id}"
