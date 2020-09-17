""" celery tasks to process camunda external tasks"""
from django.conf import settings

from celery.utils.log import get_task_logger
from celery_once import QueueOnce
from timeline_logger.models import TimelineLog

from bptl.camunda.api import complete
from bptl.camunda.models import ExternalTask
from bptl.camunda.utils import fetch_and_lock
from bptl.tasks.api import execute
from bptl.utils.constants import Statuses

from ..celery import app
from .utils import fail_task

logger = get_task_logger(__name__)

__all__ = ("task_fetch_and_lock", "task_execute_and_complete")


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
def task_fetch_and_lock():
    logger.debug("Fetching and locking tasks (long poll)")
    worker_id, num_tasks, tasks = fetch_and_lock(
        settings.MAX_TASKS,
        # convert to milliseconds
        long_polling_timeout=settings.LONG_POLLING_TIMEOUT_MINUTES * 60 * 1000,
    )

    logger.info("Fetched %r tasks with %r", num_tasks, worker_id)

    for task in tasks:
        # initial logging
        TimelineLog.objects.create(
            content_object=task, extra_data={"status": task.status}
        )

        task_execute_and_complete.delay(task.id)

    # once we're completed, which may be way within the timeout, we need to-reschedule
    # a new long-poll! this needs to run _after_ the current task has exited, otherwise
    # the celery-once lock kicks in
    task_schedule_new_fetch_and_lock.apply_async(
        countdown=0.5, 
    )
    return num_tasks


@app.task()
def task_schedule_new_fetch_and_lock():
    """
    Schedule a new long-poll.

    The scheduling needs to be done through a separate task, and not from inside the
    task itself as the run-once lock is checked while scheduling rather then at
    execution time.
    """
    task_fetch_and_lock.delay()


@app.task()
def task_execute_and_complete(fetched_task_id):
    logger.info("Received task execution request (ID %d)", fetched_task_id)
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
        fail_task(fetched_task)
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
