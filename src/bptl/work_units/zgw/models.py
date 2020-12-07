from django.db import models
from django.utils.translation import ugettext_lazy as _


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
        db_table = "tasks_defaultservice"
        verbose_name = _("default service")
        verbose_name_plural = _("default services")
        unique_together = (
            ("task_mapping", "service"),
            ("task_mapping", "alias"),
        )

    def __str__(self):
        return f"{self.task_mapping} / {self.alias}"
