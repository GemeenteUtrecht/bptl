""" celery tasks to process openklant interne tasks"""

from django.conf import settings

import requests
from celery.utils.log import get_task_logger
from celery_once import QueueOnce
from timeline_logger.models import TimelineLog

from bptl.openklant.utils import fetch_and_change_status
from bptl.tasks.api import TaskExpired, execute
from bptl.tasks.registry import register
from bptl.utils.constants import Statuses
from bptl.utils.decorators import retry

from ..celery import app
from .models import OpenKlantInternalTaskModel

logger = get_task_logger(__name__)

__all__ = ("task_fetch", "task_execute")


@app.task(
    base=QueueOnce,
    autoretry_for=(Exception,),  # if something goes wrong, automatically retry the task
    retry_backoff=True,
    once={
        "graceful": True,  # raise no exception if we're scheduling this more often (beat!)
        "timeout": (60),  # timeout if something goes wrong, in seconds
    },
)
def task_fetch_and_patch():
    logger.debug("Fetching and locking tasks (long poll)")
    worker_id, num_tasks, tasks = fetch_and_change_status()
    logger.info("Fetched %r tasks with %r", num_tasks, worker_id)

    for task in tasks:
        # initial logging
        TimelineLog.objects.create(
            content_object=task, extra_data={"status": task.status}
        )

        task_execute.delay(task.id)

    # once we're completed, which may be way within the timeout, we need to-reschedule
    # a new long-poll! this needs to run _after_ the current task has exited, otherwise
    # the celery-once lock kicks in
    task_schedule_new_fetch_and_patch.apply_async(
        countdown=15,
    )
    return num_tasks


@app.task()
def task_schedule_new_fetch_and_patch():
    """
    Schedule a new long-poll.

    The scheduling needs to be done through a separate task, and not from inside the
    task itself as the run-once lock is checked while scheduling rather then at
    execution time.
    """
    task_fetch_and_patch.delay()


@app.task()
def task_execute(fetched_task_id):
    logger.info("Received task execution request (ID %d)", fetched_task_id)
    fetched_task = OpenKlantInternalTaskModel.objects.get(id=fetched_task_id)

    # make task idempotent
    if fetched_task.status != Statuses.initial:
        logger.warning("Task %r has been already run", fetched_task_id)
        return

    task_uuid = fetched_task.task_uuid
    logger.info("Task UUID is %s", task_uuid)

    fetched_task.status = Statuses.in_progress
    fetched_task.save(update_fields=["status"])

    # Catch and retry on http errors other than 500
    @retry(
        times=3,
        exceptions=(requests.HTTPError,),
        condition=lambda exc: exc.response.status_code == 500,
        on_failure=fail_task,
    )
    def _execute(fetched_task: OpenKlantInternalTaskModel):
        execute(fetched_task, registry=register)

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
    return
