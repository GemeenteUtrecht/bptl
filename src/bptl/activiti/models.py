from urllib.parse import urljoin

from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel

from bptl.tasks.models import BaseTask


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


class ServiceTask(BaseTask):
    """
    A single activiti task which request bptl API
    """

    def __str__(self):
        return f"{self.topic_name} / {self.id}"

    class Meta:
        verbose_name = _("aervice task")
        verbose_name_plural = _("service tasks")
