from zds_client.schema import get_operation_url
from zgw_consumers.client import ZGWClient

from bptl.tasks.base import BaseTask, check_variable
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

    # Get variables
    variables = task.get_variables()

    # Build url
    client = get_client(task)
    review_request_id = check_variable(variables, "kownslReviewRequestId")
    operation_id = "reviewrequest_retrieve"
    url = get_operation_url(
        client.schema,
        operation_id,
        base_url=client.base_url,
        uuid=review_request_id,
    )
    review_request = client.request(url, operation_id)
    return review_request
