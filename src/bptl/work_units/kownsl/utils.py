from zgw_consumers.client import ZGWClient

from bptl.tasks.base import BaseTask, MissingVariable, check_variable
from bptl.tasks.models import TaskMapping


def get_client(task: BaseTask, alias: str = "kownsl") -> ZGWClient:
    default_services = TaskMapping.objects.get(
        topic_name=task.topic_name
    ).defaultservice_set.select_related("service")
    services_by_alias = {svc.alias: svc.service for svc in default_services}
    if alias not in services_by_alias:
        raise RuntimeError(f"Service alias '{alias}' not found.")

    client = services_by_alias[alias].build_client()
    client._log.task = task

    return client


def get_review_request(task: BaseTask) -> dict:
    """
    Get a single review request from kownsl.
    """
    variables = task.get_variables()

    zaak_url = check_variable(variables, "zaakUrl")
    client = get_client(task)
    resp_data = client.list(
        "reviewrequest",
        query_params={"for_zaak": zaak_url},
    )

    request_id = check_variable(variables, "kownslReviewRequestId")
    for review_request in resp_data:
        if review_request["id"] == request_id:
            return review_request

    raise MissingVariable(f"Review request: {request_id} not found.")
