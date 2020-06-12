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

    # TODO: inject auth when it's set up
    # services_vars = task.get_variables().get("services", {})
    # token = services_vars.get(alias, {}).get("token")
    # if token is None:
    #     raise RuntimeError(f"No 'token' key present in services config for alias '{alias}'")
    # client.set_auth_value(f"Token {token}")

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
        "reviewrequest", data={"advice_zaak": zaak_url}, uuid=request_id,
    )

    return {
        "doReviewUrl": resp_data["frontend_url"],
    }
