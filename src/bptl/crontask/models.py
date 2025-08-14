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

    pass
