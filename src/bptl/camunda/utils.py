"""
Module for Camunda API interaction.

TODO: fetch the handled/known topics from the DB and pass that to the fetch and lock
call.
"""
from typing import List, Optional, Tuple

from dateutil import parser
from django_camunda.client import get_client_class

from bptl.tasks.models import TaskMapping
from bptl.utils.typing import Object, ProcessVariables

from .models import ExternalTask, get_worker_id

LOCK_DURATION = 60 * 10  # 10 minutes


def fetch_and_lock(max_tasks: int) -> Tuple[str, int, list]:
    """
    Fetch and lock a number of external tasks.

    API reference: https://docs.camunda.org/manual/7.12/reference/rest/external-task/fetch/
    """
    camunda = get_client_class()()

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
    external_tasks: List[Object] = camunda.request(
        "external-task/fetchAndLock",
        method="POST",
        json={"workerId": worker_id, "maxTasks": max_tasks, "topics": topics,},
    )

    fetched = []
    for task in external_tasks:
        fetched.append(
            ExternalTask.objects.create(
                worker_id=worker_id,
                topic_name=task["topic_name"],
                priority=task["priority"],
                task_id=task["id"],
                lock_expires_at=parser.parse(task["lock_expiration_time"]),
                variables=task["variables"],
            )
        )

    return (worker_id, len(fetched), fetched)


def complete_task(
    task: ExternalTask, variables: Optional[ProcessVariables] = None
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
