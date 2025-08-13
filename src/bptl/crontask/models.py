"""
Database models to keep track of external tasks fetched from Camunda.

We save tasks in our own database in case of crashes and for dev purposes, so that we
can pick up work load again.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_camunda.client import get_client
from django_camunda.utils import deserialize_variable

from bptl.tasks.models import BaseTask
from bptl.tasks.utils import get_worker_id


class CronTask(BaseTask):
    """
    A single cron task that was assigned to a worker.

    """

    def __init__(self, *args, topic_name: str = "", variables: dict = None, **kwargs):
        if not topic_name or not variables:
            raise ValueError("Both topic_name and variables are required.")

        self.topic_name = topic_name
        self.variables = variables

        return super().__init__(*args, **kwargs)
