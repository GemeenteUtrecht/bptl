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
    # Get gevraagde handelingen in a list of strings - caching gets cleared on every save of an InterneTask object.
    return [t.gevraagde_handeling for t in InterneTask.objects.all()]


def fetch_and_patch(
    openklant_config: Optional[OpenKlantConfig] = None,
) -> Tuple[str, int, list]:
    """
    Fetch an internal task
    """
    openklant_config = (
        OpenKlantConfig.get_solo() if not openklant_config else openklant_config
    )
    openklant_client = get_openklant_client(openklant_config)

    # Get all tasks that still need to be "verwerkt"
    openklant_tasks = get_paginated_results(
        openklant_client,
        "internetaken",
        query_params={"status": "te_verwerken"},
    )

    # Filter out tasks that have an InterneTask model in BPTL.
    gevraagde_handelingen = get_gevraagde_handelingen()
    openklant_tasks = [
        t
        for t in openklant_tasks
        if t.get("gevraagdeHandeling") in gevraagde_handelingen
    ]

    # Update status in open klant to "verwerkt"
    for task in openklant_tasks:
        openklant_client.partial_update(
            "internetaak", {"status": "verwerkt"}, url=task["url"]
        )

    worker_id = get_worker_id()
    fetched = []
    for task in openklant_tasks:
        fetched.append(
            OpenKlantInternalTaskModel.objects.create(
                worker_id=worker_id,
                topic_name=task["gevraagdeHandeling"],
                task_id=task["uuid"],
                variables=task,
            )
        )

    return (worker_id, len(fetched), fetched)


def save_failed_task(task, exception):
    """Save the failed task and the reason for failure."""
    task, created = FailedOpenKlantTasks.objects.update_or_create(
        task=task,
        defaults={"reason": str(exception)},
    )

    openklant_client = get_openklant_client()
    toelichting = task.variables.get("toelichting", "")
    toelichting = "[BPTL] - {tijd}: {bericht}. \n\n {toelichting}".format(
        tijd=datetime.now().isoformat(),
        bericht="Mail versturen is mislukt.",
        toelichting=toelichting,
    )

    # Update the toelichting of the task in OpenKlant to include failed message.
    openklant_client.partial_update(
        "internetaak",
        {"toelichting": toelichting},
        url=task.task.variables["url"],
    )
