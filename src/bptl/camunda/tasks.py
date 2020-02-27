""" celery tasks to process camunda external tasks"""
from django.conf import settings

from celery.utils.log import get_task_logger
from timeline_logger.models import TimelineLog

from bptl.camunda.api import complete
from bptl.camunda.models import ExternalTask
from bptl.camunda.utils import fetch_and_lock
from bptl.tasks.api import execute
from bptl.utils.constants import Statuses

from ..celery import app

logger = get_task_logger(__name__)

__all__ = ("task_fetch_and_lock", "task_execute_and_complete")


@app.task()
def task_fetch_and_lock():
    worker_id, num_tasks, tasks = fetch_and_lock(settings.MAX_TASKS)

    logger.info("fetched %r tasks with %r", num_tasks, worker_id)

    for task in tasks:
        # initial logging
        TimelineLog.objects.create(
            content_object=task, extra_data={"status": task.status}
        )

        task_execute_and_complete.delay(task.id)
    return num_tasks


@app.task()
def task_execute_and_complete(fetched_task_id):
    fetched_task = ExternalTask.objects.get(id=fetched_task_id)

    # make task idempotent
    if fetched_task.status != Statuses.initial:
        logger.warning("Task %r has been already run", fetched_task_id)
        return

    fetched_task.status = Statuses.in_progress
    fetched_task.save(update_fields=["status"])

    # execute
    try:
        execute(fetched_task)
    except Exception as exc:
        logger.warning(
            "Task %r has failed during execution with error: %r",
            fetched_task_id,
            exc,
            exc_info=True,
        )

        return

    logger.info("Task %r is executed", fetched_task_id)

    # complete
    try:
        complete(fetched_task)
    except Exception as exc:
        logger.warning(
            "Task %r has failed during sending process with error: %r",
            fetched_task_id,
            exc,
            exc_info=True,
        )

        return

    logger.info("Task %r is completed", fetched_task_id)
