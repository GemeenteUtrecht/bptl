"""
Module for Camunda API interaction.
"""

import json
import logging
import uuid
from typing import List, Optional, Tuple, Union

import requests
from dateutil import parser
from timeline_logger.models import TimelineLog

from bptl.tasks.constants import EngineTypes
from bptl.tasks.models import TaskMapping
from bptl.tasks.utils import get_worker_id
from bptl.utils.decorators import retry
from bptl.utils.typing import Object, ProcessVariables
from bptl.work_units.zgw.utils import get_paginated_results

from .client import get_openklant_client
from .models import OpenKlantConfig, OpenKlantInternalTaskModel

logger = logging.getLogger(__name__)


def fetch_and_change_status(
    openklant_config: Optional[OpenKlantConfig] = None,
) -> Tuple[str, int, list]:
    """
    Fetch an internal task
    """
    # Fetch the mappings that are known (and active!) in this configured instance only
    mappings = TaskMapping.objects.filter(
        engine_type=EngineTypes.openklant, active=True
    )
    openklant_config = (
        OpenKlantConfig.get_solo() if not openklant_config else openklant_config
    )
    actor = openklant_config.actor.name
    openklant_client = get_openklant_client(openklant_config)
    openklant_tasks: List[Object] = get_paginated_results(
        openklant_client,
        "internetaken",
        query_params={"actoren__naam": actor, "status": "te_verwerken"},
    )

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
