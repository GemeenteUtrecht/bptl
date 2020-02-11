"""
Database models to keep track of external tasks fetched from Camunda.

We save tasks in our own database in case of crashes and for dev purposes, so that we
can pick up work load again.
"""
import uuid

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .constants import Statuses


def get_worker_id() -> str:
    prefix = "bptl"
    guid = uuid.uuid4()
    return f"{prefix}-{guid}"


class ExternalTask(models.Model):
    """
    A single task that was retrieved by the worker.

    We keep a number of fields to identify/match the tasks in the remote Camunda
    installation.
    """

    worker_id = models.CharField(
        default=get_worker_id,
        max_length=255,
        help_text=_(
            "The worker ID that picked up the task. Only the same "
            "worker ID is allowed to unlock/modify the task. Used as a lock."
        ),
    )
    topic_name = models.CharField(
        _("topic name"),
        max_length=255,
        help_text=_(
            "External tasks get published to a certain topic. Topics determine which "
            "functions need to run for a task."
        ),
    )
    priority = models.PositiveIntegerField(_("priority"), null=True, blank=True)
    task_id = models.CharField(_("task id"), max_length=50)
    lock_expires_at = models.DateTimeField(_("lock expires at"), null=True, blank=True)
    variables = JSONField(default=dict)
    status = models.CharField(
        _("status"),
        max_length=50,
        choices=Statuses.choices,
        default=Statuses.initial,
        help_text=_("The current status of task processing"),
    )
    result_variables = JSONField(default=dict)

    class Meta:
        verbose_name = _("fetched task")
        verbose_name_plural = _("fetched tasks")

    def __str__(self):
        return f"{self.topic_name} / {self.task_id}"

    @property
    def expired(self) -> bool:
        if self.lock_expires_at is None:
            return False
        return self.lock_expires_at <= timezone.now()

    @property
    def flat_variables(self) -> dict:
        return {k: v["value"] for k, v in self.variables.items()}
