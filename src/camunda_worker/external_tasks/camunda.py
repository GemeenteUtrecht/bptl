"""
Module for Camunda API interaction.

TODO: fetch the handled/known topics from the DB and pass that to the fetch and lock
call.
"""
from typing import List, Optional, Tuple

from django_camunda.client import get_client_class

from camunda_worker.utils.typing import Object, ProcessVariables

from .models import FetchedTask, get_worker_id

TOPIC = "zaak-initialize"
LOCK_DURATION = 60 * 10  # 10 minutes


def fetch_and_lock(max_tasks: int) -> Tuple[str, int]:
    """
    Fetch and lock a number of external tasks.

    API reference: https://docs.camunda.org/manual/7.12/reference/rest/external-task/fetch/
    """
    camunda = get_client_class()()

    worker_id = get_worker_id()
    external_tasks: List[Object] = camunda.request(
        "external-task/fetchAndLock",
        method="POST",
        json={
            "workerId": worker_id,
            "maxTasks": max_tasks,
            "topics": [
                {
                    "topicName": TOPIC,
                    "lockDuration": LOCK_DURATION * 1000,  # API expects miliseconds
                }
            ],
        },
    )

    fetched = []
    for task in external_tasks:
        fetched.append(
            FetchedTask(
                worker_id=worker_id,
                topic_name=task["topic_name"],
                priority=task["priority"],
                task_id=task["id"],
                lock_expires_at=task["lock_expiration_time"],
                variables=task["variables"],
            )
        )

    FetchedTask.objects.bulk_create(fetched)

    return (worker_id, len(fetched))


def complete_task(
    task: FetchedTask, variables: Optional[ProcessVariables] = None
) -> None:
    """
    Complete an External Task, while optionally setting process variables.

    API reference: https://docs.camunda.org/manual/7.12/reference/rest/external-task/post-complete/

    Note that we currently only support setting process variables and not local task
    variables.
    """
    camunda = get_client_class()()
    serialized_variables = (
        {name: {"value": value} for name, value in variables.items()}
        if variables
        else {}
    )

    body = {
        "workerId": task.worker_id,
        "variables": serialized_variables,
    }
    camunda.request(f"external-task/{task.task_id}/complete", method="POST", json=body)
