"""
Module for Camunda API interaction.
"""
from typing import List

from django_camunda.client import Camunda

from camunda_worker.utils.typing import Object

from .models import FetchedTask, get_worker_id


def fetch_and_lock(max_tasks: int) -> List[Object]:
    """
    Fetch and lock a number of external tasks.

    API reference: https://docs.camunda.org/manual/7.12/reference/rest/external-task/fetch/
    """
    camunda = Camunda()

    worker_id = get_worker_id()
    external_tasks = camunda.request(
        "fetchAndLock",
        method="POST",
        json={"workerId": worker_id, "maxTasks": max_tasks,},
    )

    fetched = []
    for task in external_tasks:
        fetched.append(
            FetchedTask(
                worker_id=worker_id,
                topic_name=task["topic_name"],
                priority=task["priority"],
                task_id=task["id"],
                variables=task["variables"],
            )
        )

    FetchedTask.objects.bulk_create(fetched)
