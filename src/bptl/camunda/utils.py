"""
Module for Camunda API interaction.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests
from dateutil import parser
from django_camunda.client import get_client_class
from django_camunda.types import JSONPrimitive

from bptl.tasks.models import TaskMapping
from bptl.utils.typing import Object, ProcessVariables

from .models import ExternalTask, get_worker_id

logger = logging.getLogger(__name__)

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

    If a task variable ``callbackUrl`` is available, a post request is made to it.

    Note that we currently only support setting process variables and not local task
    variables.
    """
    task_variables = task.get_variables()
    camunda = get_client_class()()

    serialized_variables = (
        {name: serialize_variable(value) for name, value in variables.items()}
        if variables
        else {}
    )

    body = {
        "workerId": task.worker_id,
        "variables": serialized_variables,
    }
    camunda.request(f"external-task/{task.task_id}/complete", method="POST", json=body)

    callback_url = task_variables.get("callbackUrl", "")
    assert isinstance(callback_url, str), "URLs must be of the type string"
    if callback_url:
        logger.info("Calling callback url for task %s", task)
        response = requests.post(callback_url)
        logger.info("Callback response status code: %d", response.status_code)
        response.raise_for_status()


def serialize_variable(value: Any) -> Dict[str, JSONPrimitive]:
    if isinstance(value, str):
        return {"type": "String", "value": value}

    if value is None:
        return {"type": "Null", "value": "null"}

    if isinstance(value, (dict, list)):
        serialized = json.dumps(value)
        return {"type": "json", "value": serialized}

    if isinstance(value, int):
        return {"type": "Integer", "value": value}

    raise NotImplementedError(f"Type {type(value)} is not implemented yet")


def deserialize_variable(variable: Dict[str, Any]) -> Any:
    var_type = variable.get("type", "String").lower()
    if var_type == "string":
        return variable["value"]

    if var_type in ("integer", "short", "long"):
        return int(variable["value"])

    if var_type == "json":
        return json.loads(variable["value"])

    raise NotImplementedError(f"Type {var_type} is not implemented yet")


def fail_task(task: ExternalTask, reason: str = "") -> None:
    """
    Mark an external task as failed.
    """
    raise Exception("foo")
