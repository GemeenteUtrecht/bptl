from django.db import models
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel

from bptl.tasks.models import BaseTask


class ActivitiConfig(SingletonModel):
    """configuration of Activiti service, including base url and credentials"""

    root_url = models.URLField(
        _("activiti root"),
        help_text=_(
            "Root URL where activiti is installed. The REST api "
            "path is appended to this."
        ),
        default="https://activiti.utrechtproeftuin.nl/activiti-app/api/",
    )
    auth_header = models.TextField(
        _("authorization header"),
        blank=True,
        help_text=_(
            "HTTP Authorization header value, required if the API is not open."
        ),
    )
    enterprise = models.BooleanField(
        _("is enterprise"),
        default=True,
        help_text=_("Boolean indicating if the enterprise edition of Activiti is used"),
    )

    class Meta:
        verbose_name = _("Activiti configuration")

    def __str__(self):
        return self.root_url


class ServiceTask(BaseTask):
    """
    A single activiti task which request bptl API
    """

    class Meta:
        verbose_name = _("service task")
        verbose_name_plural = _("service tasks")

    def __str__(self):
        return f"{self.topic_name} / {self.id}"
