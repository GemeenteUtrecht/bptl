"""
Database models to keep track of cron tasks created by django_celery_beat.

We save tasks in our own database in case of crashes and for dev purposes, so that we
can pick up work load again.
"""

from bptl.tasks.models import BaseTask


class CronTask(BaseTask):
    """
    A single cron task that was assigned to a worker.

    """

    def __init__(self, topic_name: str = "", variables: dict = None):
        if not topic_name or not variables:
            raise ValueError("Both topic_name and variables are required.")

        self.topic_name = topic_name
        self.variables = variables

        return super().__init__(*args, **kwargs)
