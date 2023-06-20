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

from django_camunda.client import get_client
from django_camunda.utils import deserialize_variable

from bptl.tasks.models import BaseTask


def get_worker_id() -> str:
    prefix = "bptl"
    guid = uuid.uuid4()
    return f"{prefix}-{guid}"


class ExternalTask(BaseTask):
    """
    A single Camunda task that was retrieved by the worker.

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
    priority = models.PositiveIntegerField(_("priority"), null=True, blank=True)
    task_id = models.CharField(_("task id"), max_length=50)
    instance_id = models.CharField(_("process instance id"), max_length=50)
    lock_expires_at = models.DateTimeField(_("lock expires at"), null=True, blank=True)
    camunda_error = JSONField(
        _("camunda error"),
        blank=True,
        null=True,
        default=None,
    )

    class Meta:
        verbose_name = _("external task")
        verbose_name_plural = _("external tasks")

    def __str__(self):
        return f"{self.topic_name} / {self.task_id}"

    @property
    def expired(self) -> bool:
        if self.lock_expires_at is None:
            return False
        return self.lock_expires_at <= timezone.now()

    def get_variables(self) -> dict:
        return {k: deserialize_variable(v) for k, v in self.variables.items()}

    def get_process_instance_id(self) -> str:
        camunda = get_client()
        task = camunda.get(f"external-task/{self.task_id}")
        return task["process_instance_id"]
