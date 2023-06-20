"""
Module for Camunda API interaction.
"""
import json
import logging
from typing import List, Optional, Tuple, Union

import requests
from dateutil import parser
from django_camunda.client import get_client
from django_camunda.utils import serialize_variable
from timeline_logger.models import TimelineLog

from bptl.tasks.models import TaskMapping
from bptl.utils.decorators import retry
from bptl.utils.typing import Object, ProcessVariables

from .models import ExternalTask, get_worker_id

logger = logging.getLogger(__name__)

LOCK_DURATION = 60 * 10  # 10 minutes


def fetch_and_lock(max_tasks: int, long_polling_timeout=None) -> Tuple[str, int, list]:
    """
    Fetch and lock a number of external tasks.
    API reference: https://docs.camunda.org/manual/7.12/reference/rest/external-task/fetch/
    """
    camunda = get_client()

    # Fetch the topics that are known (and active!) in this configured instance only
    mappings = TaskMapping.objects.filter(active=True)
    topics = [
        {
            "topicName": mapping.topic_name,
            "lockDuration": LOCK_DURATION * 1000,  # API expects miliseconds
        }
        for mapping in mappings
    ]

    worker_id = get_worker_id()
    body = {
        "workerId": worker_id,
        "maxTasks": max_tasks,
        "topics": topics,
    }
    if long_polling_timeout:
        body["asyncResponseTimeout"] = long_polling_timeout

    external_tasks: List[Object] = camunda.request(
        "external-task/fetchAndLock", method="POST", json=body
    )

    fetched = []
    for task in external_tasks:
        fetched.append(
            ExternalTask.objects.create(
                worker_id=worker_id,
                topic_name=task["topic_name"],
                priority=task["priority"],
                task_id=task["id"],
                instance_id=task["process_instance_id"],
                lock_expires_at=parser.parse(task["lock_expiration_time"]),
                variables=task["variables"],
            )
        )

    return (worker_id, len(fetched), fetched)


def fail_retried_complete(
    exception: Exception,
    task: ExternalTask,
    variables: Optional[ProcessVariables] = None,
):
    fail_task(task, reason=exception.args[0])


@retry(
    times=3,
    exceptions=(requests.HTTPError,),
    condition=lambda exc: exc.response.status_code == 500,
    on_failure=fail_retried_complete,
)
def complete_task(
    task: ExternalTask, variables: Optional[ProcessVariables] = None
) -> None:
    """
    Complete an External Task, while optionally setting process variables.

    API reference: https://docs.camunda.org/manual/7.12/reference/rest/external-task/post-complete/

    If a task variable ``callbackUrl`` is available, a post request is made to it.

    Note that we currently only support setting process variables and not local task
    variables.

    Camunda performs optimistic table locking, see the `docs`_. This results in HTTP
    500 exceptions being thrown when concurrent mutations to the process instance
    happen. The recommended way to deal with this by Camunda is to retry the operation
    to reach eventual consistency, which is why the ``@retry`` decorator applies.

    .. _docs: https://docs.camunda.org/manual/latest/user-guide/process-engine/transactions-in-processes/#common-places-where-optimistic-locking-exceptions-are-thrown  # noqa
    """
    task_variables = task.get_variables()
    camunda = get_client()

    serialized_variables = (
        {name: serialize_variable(value) for name, value in variables.items()}
        if variables
        else {}
    )

    body = {
        "workerId": task.worker_id,
        "variables": serialized_variables,
    }
    try:
        camunda.post(f"external-task/{task.task_id}/complete", json=body)
    except requests.HTTPError as exc:
        log_camunda_error(task, exc)
        raise

    callback_url = task_variables.get("callbackUrl", "")
    assert isinstance(callback_url, str), "URLs must be of the type string"
    if callback_url:
        logger.info("Calling callback url for task %s", task)
        response = requests.post(callback_url)
        logger.info("Callback response status code: %d", response.status_code)
        response.raise_for_status()


def fail_task(task: Union[ExternalTask, str], reason: str = "") -> None:
    """
    Mark an external task as failed.

    See https://docs.camunda.org/manual/7.11/reference/rest/external-task/post-failure/

    When the number of retries becomes 0, an incident is created in Camunda.
    """
    if type(task) == str:
        logger.info("Received task execution request (ID %d)", task)
        task = ExternalTask.objects.get(id=task)

    camunda = get_client()

    if not reason:
        error_lines = task.execution_error.splitlines()
        if error_lines:
            reason = error_lines[-1]

    body = {
        "workerId": task.worker_id,
        "errorMessage": reason,
        "errorDetail": task.execution_error,
        "retries": 0,  # TODO: some sort of retry policy?
        "retryTimeout": 0,
    }

    camunda.post(f"external-task/{task.task_id}/failure", json=body)


def extend_task(task: ExternalTask) -> ExternalTask:
    body = {
        "newDuration": LOCK_DURATION * 1000,  # milliseconds
        "workerId": task.worker_id,
    }

    camunda = get_client()
    camunda.post(f"external-task/{task.task_id}/extendLock", json=body)
    external_task = camunda.get(f"external-task/{task.task_id}")
    task.lock_expires_at = parser.parse(external_task["lock_expiration_time"])
    task.save()
    return task


def log_camunda_error(task: ExternalTask, exc: requests.HTTPError) -> None:
    # log Camunda errors if we get any at all
    response = getattr(exc, "response", None)
    if response is None:
        return

    try:
        error_information = response.json()
    except json.JSONDecodeError:
        error_information = None

    TimelineLog.objects.create(
        content_object=task,
        template="timeline_logger/camunda/failed_complete.txt",
        extra_data={
            "status_code": response.status_code,
            "body": error_information,
        },
    )
    task.camunda_error = error_information
    task.save(update_fields=["camunda_error"])
