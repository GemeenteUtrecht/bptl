from django.conf import settings

from celery.utils.log import get_task_logger

from camunda_worker.external_tasks.camunda import fetch_and_lock
from camunda_worker.external_tasks.constants import Statuses
from camunda_worker.external_tasks.models import FetchedTask

from ...celery import app
from ..api import complete, execute

logger = get_task_logger(__name__)

__all__ = ("task_fetch_and_lock", "task_execute_and_complete")


@app.task()
def task_fetch_and_lock():
    worker_id, num_tasks, tasks = fetch_and_lock(settings.MAX_TASKS)

    logger.info("fetched %r tasks with %r", num_tasks, worker_id)

    for task in tasks:
        task_execute_and_complete(task.id)
    return num_tasks


@app.task()
def task_execute_and_complete(fetched_task_id):
    fetched_task = FetchedTask.objects.get(id=fetched_task_id)

    fetched_task.status = Statuses.in_progress
    fetched_task.save()

    # execute
    try:
        execute(fetched_task)
    except Exception as exc:
        logger.debug("Task %r has failed with error: %r", fetched_task_id, exc)

        fetched_task.status = Statuses.failed
        fetched_task.save()

        return

    logger.info("Task %r is executed", fetched_task_id)

    # complete
    try:
        complete(fetched_task)
    except Exception as exc:
        logger.debug("Task %r has failed with error: %r", fetched_task_id, exc)

        fetched_task.status = Statuses.failed
        fetched_task.save()

        return

    logger.info("Task %r is completed", fetched_task_id)
