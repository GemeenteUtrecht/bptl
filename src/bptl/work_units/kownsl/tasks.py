from zds_client.schema import get_operation_url
from zgw_consumers.client import ZGWClient

from bptl.tasks.base import BaseTask, check_variable
from bptl.tasks.models import TaskMapping
from bptl.tasks.registry import register


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


@register
def finalize_review_request(task: BaseTask) -> dict:
    """
    Update a review request in Kownsl.

    Review requests can be requests for advice or approval. This tasks registers the
    case used for the actual review with the review request, and derives the frontend
    URL for end-users where they can submit their review.

    In the task binding, the service with alias ``kownsl`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``reviewRequestId``: the identifier of the Kowns review request, used to update
      the object in the API.
    * ``zaakUrl``: URL reference to the zaak used for the review itself.

    **Sets the process variables**

    * ``doReviewUrl``: the frontend URL that reviewers visit to submit the review

    """
    variables = task.get_variables()

    request_id = check_variable(variables, "reviewRequestId")
    zaak_url = check_variable(variables, "zaakUrl")

    client = get_client(task)

    resp_data = client.partial_update(
        "reviewrequest", data={"review_zaak": zaak_url}, uuid=request_id,
    )

    return {
        "doReviewUrl": resp_data["frontend_url"],
    }


@register
def get_approval_status(task: BaseTask) -> dict:
    """
    Get the result of an approval review request.

    Once all reviewers have submitted their approval or rejection, derive the end-result
    from the review session. If all reviewers approve, the result is positive. If any
    rejections are present, the result is negative.

    In the task binding, the service with alias ``kownsl`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``reviewRequestId``: the identifier of the Kowns review request, used to update
      the object in the API.
    * ``zaakUrl``: URL reference to the zaak used for the review itself.

    **Sets the process variables**

    * ``approvalResult``: a JSON-object containing meta-data about the result:

      .. code-block:: json

         {
            "approved": true,
            "num_approved": 3,
            "num_rejected": 0
         }
    """
    client = get_client(task)
    variables = task.get_variables()

    # TODO: switch from zaak-based retrieval to review-request based
    zaak_url = check_variable(variables, "zaakUrl")
    check_variable(variables, "reviewRequestId")

    operation_id = "approvalcollection_retrieve"
    url = get_operation_url(client.schema, operation_id, base_url=client.base_url)

    params = {"objectUrl": zaak_url}
    approval_collection = client.request(
        url, operation_id, request_kwargs={"params": params},
    )

    num_approved = 0
    num_rejected = 0
    for approval in approval_collection["approvals"]:
        if approval["approved"]:
            num_approved += 1
        else:
            num_rejected += 1

    return {
        "approvalResult": {
            "approved": num_approved > 0 and num_rejected == 0,
            "num_approved": num_approved,
            "num_rejected": num_rejected,
        },
    }
