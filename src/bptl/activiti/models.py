from urllib.parse import urljoin

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel

from bptl.utils.constants import Statuses


class ActivitiConfig(SingletonModel):
    """ configuration of Activiti service, including base url and credentials """

    root_url = models.URLField(
        _("camunda root"),
        help_text=_(
            "Root URL where activiti is installed. The REST api "
            "path is appended to this."
        ),
        default="https://activiti.utrechtproeftuin.nl/activiti-app/api/",
    )
    rest_api_path = models.CharField(
        _("REST api path"), max_length=255, default="management/engine"
    )
    auth_header = models.TextField(
        _("authorization header"),
        blank=True,
        help_text=_(
            "HTTP Authorization header value, required if the API is not open."
        ),
    )

    class Meta:
        verbose_name = _("Activiti configuration")

    def __str__(self):
        return self.api_root

    def save(self, *args, **kwargs):
        if self.rest_api_path.startswith("/"):
            self.rest_api_path = self.rest_api_path[1:]

        if not self.rest_api_path.endswith("/"):
            self.rest_api_path = f"{self.rest_api_path}/"

        super().save(*args, **kwargs)

    @property
    def api_root(self) -> str:
        assert not self.rest_api_path.startswith("/")
        assert self.rest_api_path.endswith("/")
        return urljoin(self.root_url, self.rest_api_path)


class ServiceTask(models.Model):
    """
    A single task which request bptl API
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

    def __str__(self):
        return f"{self.topic_name} / {self.id}"
