""" celery tasks to process `cron` tasks"""

from django.conf import settings

import requests
from celery.utils.log import get_task_logger
from celery_once import QueueOnce
from timeline_logger.models import TimelineLog

from bptl.tasks.api import TaskExpired, execute
from bptl.tasks.registry import register
from bptl.utils.constants import Statuses
from bptl.utils.decorators import retry

from ..celery import app
from .models import CronTask

logger = get_task_logger(__name__)

__all__ = ("task_create_cron_task", "cron_task_execute_and_complete")


@app.task(
    base=QueueOnce,
    autoretry_for=(Exception,),  # if something goes wrong, automatically retry the task
    retry_backoff=True,
    once={
        "graceful": True,  # raise no exception if we're scheduling this more often (beat!)
        "timeout": (
            (settings.LONG_POLLING_TIMEOUT_MINUTES * 60) + 1
        ),  # timeout if something goes wrong, in seconds
    },
)
def task_create_cron_task(*args, **kwargs):
    logger.debug("Creating cron task")
    task = CronTask.objects.create(**kwargs)
    logger.info("Created `cron` tasks with task id %s" % task.id)

    # initial logging
    TimelineLog.objects.create(content_object=task, extra_data={"status": task.status})

    cron_task_execute_and_complete.delay(task.id)

    return num_tasks


@app.task()
def cron_task_execute_and_complete(fetched_task_id):
    logger.info("Received task execution request (ID %d)", fetched_task_id)
    fetched_task = CronTask.objects.get(id=fetched_task_id)

    # make task idempotent
    if fetched_task.status != Statuses.initial:
        logger.warning("Task %r has been already run", fetched_task_id)
        return

    fetched_task.status = Statuses.in_progress
    fetched_task.save(update_fields=["status"])

    # Catch and retry on http errors other than 500
    @retry(
        times=3,
        exceptions=(requests.HTTPError,),
        condition=lambda exc: exc.response.status_code == 500,
    )
    def _execute(fetched_task: CronTask):
        return execute(fetched_task, registry=register)

    try:
        _execute(fetched_task)
    except Exception as exc:
        logger.warning(
            "Task %r has failed during execution with error: %r",
            fetched_task_id,
            exc,
            exc_info=True,
        )
        return

    logger.info("Task %r is executed", fetched_task_id)
