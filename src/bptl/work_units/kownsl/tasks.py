import datetime

from zds_client.schema import get_operation_url
from zgw_consumers.client import ZGWClient

from bptl.tasks.base import BaseTask, MissingVariable, check_variable
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


def get_review_request(task: BaseTask) -> dict:
    """
    Get a single review request from kownsl.
    """
    variables = task.get_variables()

    zaak_url = check_variable(variables, "hoofdZaakUrl")
    client = get_client(task)
    resp_data = client.list(
        "reviewrequest",
        query_params={"for_zaak": zaak_url},
    )

    request_id = check_variable(variables, "reviewRequestId")
    for review_request in resp_data:
        if review_request["id"] == request_id:
            return review_request

    raise MissingVariable(f"Review request: {request_id} not found.")


@register
def finalize_review_request(task: BaseTask) -> dict:
    """
    Update a review request in Kownsl.

    DEPRECATED - do not use anymore.

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
        "reviewrequest",
        data={"review_zaak": zaak_url},
        uuid=request_id,
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
    review_request_id = check_variable(variables, "reviewRequestId")

    operation_id = "reviewrequest_approvals"
    url = get_operation_url(
        client.schema,
        operation_id,
        base_url=client.base_url,
        uuid=review_request_id,
    )

    approvals = client.request(url, operation_id)

    num_approved, num_rejected = 0, 0
    for approval in approvals:
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


@register
def get_review_response_status(task: BaseTask) -> dict:
    """
    Get the reviewers who have not yet responded to a review request so that
    a reminder email can be sent to them if they exist.

    In the task binding, the service with alias ``kownsl`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``reviewRequestId``: the identifier of the Kowns review request, used to update
      the object in the API.
    * ``hoofdZaakUrl``: URL reference to the zaak used for the review itself.
    * ``kownslUsers``: list of usernames that have been configured in the review request configuration.

    **Sets the process variables**

    * ``remindThese``: a JSON-object containing a list of usernames who need reminding:

      .. code-block:: json
            [
                "user1",
                "user2",
            ]
    """

    # Get the review request with id as given in variables
    review_request = get_review_request(task)

    review_request_id = review_request.get("id")

    # Get review request type to set operation_id
    review_type = review_request.get("review_type")
    if review_type == "approval":
        operation_id = "reviewrequest_approvals"
    else:
        operation_id = "reviewrequest_advices"

    client = get_client(task)
    url = get_operation_url(
        client.schema,
        operation_id,
        base_url=client.base_url,
        uuid=review_request_id,
    )

    # Get approvals/advices belong to review request
    reviews = client.request(url, operation_id)

    # Build a list of users that have responded
    already_responded = []
    for review in reviews:
        user = review["author"]
        already_responded.append(user)

    # Check who should respond
    variables = task.get_variables()
    needs_to_respond = check_variable(variables, "kownslUsers")

    # Finally figure out who hasn't responded yet
    not_responded = [
        username for username in needs_to_respond if username not in already_responded
    ]
    return {
        "remindThese": not_responded,
    }


@register
def get_review_request_reminder_date(task: BaseTask) -> dict:
    """
    Get the reminder for the set of reviewers who are requested.
    The returned value is the deadline minus one day.

    In the task binding, the service with alias ``kownsl`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``reviewRequestId``: the identifier of the Kowns review request, used to update
      the object in the API.
    * ``hoofdZaakUrl``: URL reference to the zaak used for the review itself.
    * ``kownslUsers``: list of usernames that have been configured in the review request configuration.

    **Sets the process variables**

    * ``reminderDate``: a string containing the reminder date: "2020-02-29"
    """
    # Get kownslUsers
    variables = task.get_variables()
    kownsl_users = check_variable(variables, "kownslUsers")

    # Get the review request with id as given in variables
    review_request = get_review_request(task)
    user_deadlines = review_request["user_deadlines"]

    # Get deadline belonging to that specific set of kownslUsers
    deadline_str = user_deadlines.get(kownsl_users[0])
    deadline = datetime.datetime.strptime(deadline_str, "%Y-%m-%d").date()

    # Set reminder date - 1 day less than deadline
    reminder = deadline - datetime.timedelta(days=1)
    reminder_str = reminder.strftime("%Y-%m-%d")
    return {
        "reminderDate": reminder_str,
    }
