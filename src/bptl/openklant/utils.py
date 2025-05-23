"""
Module for OpenKlant API interaction.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from bptl.tasks.utils import get_worker_id
from bptl.utils.decorators import cache
from bptl.work_units.zgw.utils import get_paginated_results

from .client import get_openklant_client
from .models import (
    FailedOpenKlantTasks,
    InterneTask,
    OpenKlantConfig,
    OpenKlantInternalTaskModel,
)

logger = logging.getLogger(__name__)


@cache("interne_task_gevraagde_handelingen")
def get_gevraagde_handelingen() -> List[str]:
    """
    Get a list of 'gevraagde handelingen' from InterneTask objects.
    Caching is cleared on every save of an InterneTask object.
    """
    return [t.gevraagde_handeling for t in InterneTask.objects.all()]


def fetch_and_patch(
    openklant_config: Optional[OpenKlantConfig] = None,
) -> Tuple[str, int, list]:
    """
    Fetch internal tasks from OpenKlant and update their status to "verwerkt".
    """
    openklant_config = openklant_config or OpenKlantConfig.get_solo()
    openklant_client = get_openklant_client(openklant_config)

    openklant_tasks = _fetch_openklant_tasks(openklant_client)
    openklant_tasks = _filter_tasks_by_gevraagde_handelingen(openklant_tasks)

    _update_tasks_status(openklant_client, openklant_tasks, status="verwerkt")

    worker_id = get_worker_id()
    fetched_tasks = _create_internal_task_models(worker_id, openklant_tasks)

    return worker_id, len(fetched_tasks), fetched_tasks


def save_failed_task(task, exception):
    """
    Save a failed task and update its status in OpenKlant with a failure message.
    """
    _save_failed_task_to_db(task, exception)
    _update_task_toelichting_in_openklant(task, exception)


def _fetch_openklant_tasks(openklant_client) -> List[dict]:
    """
    Fetch tasks from OpenKlant with status "te_verwerken".
    """
    return get_paginated_results(
        openklant_client,
        "internetaken",
        query_params={"status": "te_verwerken"},
    )


def _filter_tasks_by_gevraagde_handelingen(tasks: List[dict]) -> List[dict]:
    """
    Filter tasks to include only those with 'gevraagdeHandeling' in the allowed list.
    """
    gevraagde_handelingen = get_gevraagde_handelingen()
    return [t for t in tasks if t.get("gevraagdeHandeling") in gevraagde_handelingen]


def _update_tasks_status(openklant_client, tasks: List[dict], status: str):
    """
    Update the status of tasks in OpenKlant.
    """
    for task in tasks:
        openklant_client.partial_update(
            "internetaak", {"status": status}, url=task["url"]
        )


def _create_internal_task_models(
    worker_id: str, tasks: List[dict]
) -> List[OpenKlantInternalTaskModel]:
    """
    Create OpenKlantInternalTaskModel instances for the fetched tasks.
    """
    return [
        OpenKlantInternalTaskModel.objects.create(
            worker_id=worker_id,
            topic_name=task["gevraagdeHandeling"],
            task_id=task["uuid"],
            variables=task,
        )
        for task in tasks
    ]


def _save_failed_task_to_db(task, exception):
    """
    Save the failed task and the reason for failure to the database.
    """
    FailedOpenKlantTasks.objects.update_or_create(
        task=task,
        defaults={"reason": str(exception)},
    )


def _update_task_toelichting_in_openklant(task, exception):
    """
    Update the 'toelichting' field of the task in OpenKlant with a failure message.
    """
    openklant_client = get_openklant_client()
    toelichting = task.variables.get("toelichting", "")
    formatted_toelichting = "[BPTL] - {tijd}: {bericht} \n\n{toelichting}".format(
        tijd=datetime.now().replace(second=0, microsecond=0).isoformat(),
        bericht="Mail versturen is mislukt.",
        toelichting=toelichting,
    )
    openklant_client.partial_update(
        "internetaak",
        {"toelichting": formatted_toelichting},
        url=task.variables["url"],
    )
