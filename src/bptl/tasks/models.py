"""
Database model to map task topics and python code objects to process related tasks
"""

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from bptl.utils.constants import Statuses

from .query import TaskQuerySet


class TaskMapping(models.Model):
    topic_name = models.CharField(
        _("topic name"),
        max_length=255,
        unique=True,
        help_text=_(
            "Topic as defined in the Task of external Business Process engine. Topics are used "
            "to decide which listener to run for a task."
        ),
    )
    callback = models.CharField(
        _("callback"),
        max_length=255,
        help_text=_(
            "Listener to connect to the topic. This is a specialized piece of code "
            "that will run for each task with the configured topic."
        ),
    )
    active = models.BooleanField(_("active flag"), default=True)
    default_services = models.ManyToManyField(
        "zgw_consumers.Service",
        related_name="task_mappings",
        through="tasks.DefaultService",
    )

    objects = TaskQuerySet.as_manager()

    class Meta:
        verbose_name = _("task mapping")
        verbose_name_plural = _("task mappings")

    def __str__(self):
        return f"{self.topic_name} / {self.callback}"


class DefaultService(models.Model):
    """default ZGW services for particular tasks"""

    task_mapping = models.ForeignKey(TaskMapping, on_delete=models.CASCADE)
    service = models.ForeignKey("zgw_consumers.Service", on_delete=models.CASCADE)
    alias = models.CharField(
        _("alias"),
        max_length=100,
        help_text="Alias for the service used in the particular task",
    )

    class Meta:
        verbose_name = _("default service")
        verbose_name_plural = _("default services")
        unique_together = ("task_mapping", "service")

    def __str__(self):
        return f"{self.task_mapping} / {self.alias}"


class BaseTask(models.Model):
    """
    An external task to be processed by work units.

    Use this as the base class for process-engine specific task definitions.
    """

    topic_name = models.CharField(
        _("topic name"),
        max_length=255,
        help_text=_("Topics determine which functions need to run for a task."),
    )
    variables = JSONField(default=dict)
    status = models.CharField(
        _("status"),
        max_length=50,
        choices=Statuses.choices,
        default=Statuses.initial,
        help_text=_("The current status of task processing"),
    )
    result_variables = JSONField(default=dict)
    execution_error = models.TextField(
        _("execution error"),
        blank=True,
        help_text=_("The error that occurred during execution."),
    )

    class Meta:
        abstract = True

    def get_variables(self) -> dict:
        """
        return input variables formatted for work_unit
        """
        return self.variables
