import datetime

from bptl.tasks.base import BaseTask, check_variable
from bptl.tasks.registry import register

from .utils import get_client, get_review_request, require_kownsl_service


@register
@require_kownsl_service
def get_approval_status(task: BaseTask) -> dict:
    """
    Get the result of an approval review request.

    Once all reviewers have submitted their approval or rejection, derive the end-result
    from the review session. If all reviewers approve, the result is positive. If any
    rejections are present, the result is negative.

    In the task binding, the service with alias ``kownsl`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.

    **Optional process variables**

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    **Sets the process variables**

    * ``approvalResult``: a JSON-object containing meta-data about the result:

      .. code-block:: json

         {
            "approved": true,
            "num_approved": 3,
            "num_rejected": 0,
            "approvers": ["mpet001", "will002", "jozz001"]
         }

    """
    client = get_client(task)
    variables = task.get_variables()

    review_request_id = check_variable(variables, "kownslReviewRequestId")

    approvals = client.list(
        "review_requests_approvals", request__uuid=review_request_id
    )

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
            "approvers": [
                approval["author"]["username"]
                for approval in approvals
                if approval["approved"]
            ],
        },
    }


@register
@require_kownsl_service
def get_review_response_status(task: BaseTask) -> dict:
    """
    Get the reviewers who have not yet responded to a review request so that
    a reminder email can be sent to them if they exist.

    In the task binding, the service with alias ``kownsl`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.
    * ``kownslUsers``: list of users or groups that have been configured in the review request configuration.

    **Optional process variables**

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    **Sets the process variables**

    * ``remindThese``: a JSON-object containing a list of users or groups who need reminding:

      .. code-block:: json

            [
                "user:user1",
                "user:user2",
            ]
    """
    # Get the review request with id as given in variables
    review_request = get_review_request(task)

    # Get review request type to set operation_id
    review_type = review_request["reviewType"]
    resource = (
        "review_requests_approvals"
        if review_type == "approval"
        else "review_requests_advices"
    )

    client = get_client(task)

    # Get approvals/advices belonging to review request
    reviews = client.list(resource, request__uuid=review_request["id"])

    # Build a list of users that have responded
    already_responded = []
    for review in reviews:
        user = (
            f"group:{review['group']}"
            if review["group"]
            else f"user:{review['author']['username']}"
        )
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
@require_kownsl_service
def get_review_request_start_process_information(task: BaseTask) -> dict:
    """
    Get the process information for the review request.
    The process information consists of the:
        * deadline of the review request,
        * reminder date of the review request,
        * lock status of the review request,
        * the username of the requester,
        * and finally, the review type.

    In the task binding, the service with alias ``kownsl`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.
    * ``kownslUsers``: list of usernames that have been configured in the review request configuration.
    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    **Sets the process variables**

    * ``reminderDate``: a string containing the reminder date: "2020-02-29".
    * ``deadline``: a string containing the deadline date: "2020-03-01".
    * ``locked``: a boolean containing the lock status of the review request.
    * ``requester``: a string containing the username of the review requester.
    * ``reviewType``: a string containing the review type (i.e., "advice" or "approval").
    """
    # Get kownslUsers
    variables = task.get_variables()
    kownsl_users = check_variable(variables, "kownslUsers")

    # Get user deadlines
    review_request = get_review_request(task)
    user_deadlines = review_request["userDeadlines"]

    # Get deadline belonging to that specific set of kownslUsers
    deadline_str = user_deadlines[kownsl_users[0]]
    deadline = datetime.datetime.strptime(deadline_str, "%Y-%m-%d").date()

    # Set reminder date - 1 day less than deadline
    reminder = deadline - datetime.timedelta(days=1)
    reminder_str = reminder.strftime("%Y-%m-%d")
    return {
        "deadline": deadline_str,
        "reminderDate": reminder_str,
        "locked": review_request["locked"],
        "requester": review_request["requester"]["username"],
        "reviewType": "advies" if review_request["reviewType"] == 'advice' else "accordering",
    }




@register
@require_kownsl_service
def set_review_request_metadata(task: BaseTask) -> dict:
    """
    Set the metadata for a Kownsl review request.

    Metadata is a set of arbitrary key-value labels, allowing you to attach extra data
    required for your process routing/handling.

    **Required process variables**

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.
    * ``metadata``: a JSON structure holding key-values of the metadata. This will be
      set directly on the matching review request. Example:

      .. code-block:: json

            {
                "processInstanceId": "aProcessInstanceId"
            }

    **Optional process variables**

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    **Sets no process variables**

    """
    variables = task.get_variables()
    review_request_id = check_variable(variables, "kownslReviewRequestId")
    metadata = check_variable(variables, "metadata")

    client = get_client(task)
    client.partial_update(
        "review_requests",
        data={"metadata": metadata},
        uuid=review_request_id,
    )

    return {}


@register
@require_kownsl_service
def get_approval_toelichtingen(task: BaseTask) -> dict:
    """
    Get the "toelichtingen" of all reviewers that responded to the review request.

    **Required process variables**

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.

    **Optional process variables**

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    **Sets the process variables**

    * ``toelichtingen``: a string containing the "toelichtingen" of all reviewers.
    """
    variables = task.get_variables()
    review_request_id = check_variable(variables, "kownslReviewRequestId")
    client = get_client(task)
    # Get approvals belonging to review request
    approvals = client.list(
        "review_requests_approvals", request__uuid=review_request_id
    )

    # Get their toelichtingen
    toelichtingen = [approval["toelichting"] or "Geen" for approval in approvals]

    return {"toelichtingen": "\n\n".join(toelichtingen)}
