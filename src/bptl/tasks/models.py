"""
Database model to map task topics and python code objects to process related tasks
"""

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy as _

from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from timeline_logger.models import TimelineLog

from bptl.utils.constants import Statuses

from .constants import EngineTypes
from .query import BaseTaskQuerySet, TaskQuerySet


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
        through="DefaultService",
    )
    engine_type = models.CharField(
        _("engine_type"),
        max_length=50,
        choices=EngineTypes.choices,
        default=EngineTypes.camunda,
        help_text=_("The engine type used for the task."),
    )

    objects = TaskQuerySet.as_manager()

    class Meta:
        verbose_name = _("task mapping")
        verbose_name_plural = _("task mappings")

    def __str__(self):
        return f"{self.topic_name} / {self.callback}"


class DefaultService(models.Model):
    """default ZGW services for particular tasks"""

    task_mapping = models.ForeignKey("tasks.TaskMapping", on_delete=models.CASCADE)
    service = models.ForeignKey("zgw_consumers.Service", on_delete=models.CASCADE)
    alias = models.CharField(
        _("alias"),
        max_length=100,
        help_text="Alias for the service used in the particular task",
    )

    class Meta:
        verbose_name = _("default service")
        verbose_name_plural = _("default services")
        constraints = [
            models.UniqueConstraint(
                fields=["task_mapping", "service"],
                name="unique_task_mapping_service",
            ),
            models.UniqueConstraint(
                fields=["task_mapping", "alias"],
                name="unique_task_mapping_alias",
            ),
        ]

    def __str__(self):
        return f"{self.task_mapping} / {self.alias}"


class BaseTask(PolymorphicModel):
    """
    An external task to be processed by work units.

    Use this as the base class for process-engine specific task definitions.
    """

    topic_name = models.CharField(
        _("topic name"),
        max_length=255,
        help_text=_("Topics determine which functions need to run for a task."),
    )
    variables = models.JSONField(default=dict)
    status = models.CharField(
        _("status"),
        max_length=50,
        choices=Statuses.choices,
        default=Statuses.initial,
        help_text=_("The current status of task processing"),
    )
    result_variables = models.JSONField(default=dict)
    execution_error = models.TextField(
        _("execution error"),
        blank=True,
        help_text=_("The error that occurred during execution."),
    )
    logs = GenericRelation(TimelineLog, related_query_name="task")

    objects = PolymorphicManager.from_queryset(BaseTaskQuerySet)()

    def get_variables(self) -> dict:
        """
        return input variables formatted for work_unit
        """
        return self.variables

    def request_logs(self) -> models.QuerySet:
        return self.logs.filter(extra_data__has_key="request").order_by("-timestamp")

    def status_logs(self) -> models.QuerySet:
        return self.logs.filter(extra_data__has_key="status").order_by("-timestamp")

    def __str__(self):
        return f"{self.polymorphic_ctype}: {self.topic_name} / {self.id}"
