"""
Database model to map task topics and python code objects to process related tasks
"""

from django.db import models
from django.utils.translation import ugettext_lazy as _

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

    objects = TaskQuerySet.as_manager()

    class Meta:
        verbose_name = _("task mapping")
        verbose_name_plural = _("task mappings")

    def __str__(self):
        return f"{self.topic_name} / {self.callback}"
