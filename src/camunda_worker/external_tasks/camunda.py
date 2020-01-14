"""
Module for Camunda API interaction.
"""
from typing import List

from camunda_worker.utils.typing import Object


def fetch_and_lock(max_tasks: int) -> List[Object]:
    """
    Fetch and lock a number of external tasks.

    API reference: https://docs.camunda.org/manual/7.12/reference/rest/external-task/fetch/
    """
    pass
