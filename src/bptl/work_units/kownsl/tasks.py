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

    approvals = client.list("approval", parent_lookup_request__uuid=review_request_id)

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
    * ``kownslUsers``: list of usernames that have been configured in the review request configuration.

    **Optional process variables**

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

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

    # Get review request type to set operation_id
    review_type = review_request["review_type"]
    resource = "approval" if review_type == "approval" else "advice"

    client = get_client(task)

    # Get approvals/advices belonging to review request
    reviews = client.list(resource, parent_lookup_request__uuid=review_request["id"])

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
@require_kownsl_service
def get_review_request_reminder_date(task: BaseTask) -> dict:
    """
    Get the reminder for the set of reviewers who are requested.
    The returned value is the deadline minus one day.

    In the task binding, the service with alias ``kownsl`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.
    * ``kownslUsers``: list of usernames that have been configured in the review request configuration.

    **Optional process variables**

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    **Sets the process variables**

    * ``reminderDate``: a string containing the reminder date: "2020-02-29".
    * ``deadline``: a string containing the deadline date: "2020-03-01".
    """
    # Get kownslUsers
    variables = task.get_variables()
    kownsl_users = check_variable(variables, "kownslUsers")

    # Get user deadlines
    review_request = get_review_request(task)
    user_deadlines = review_request["user_deadlines"]

    # Get deadline belonging to that specific set of kownslUsers
    deadline_str = user_deadlines[kownsl_users[0]]
    deadline = datetime.datetime.strptime(deadline_str, "%Y-%m-%d").date()

    # Set reminder date - 1 day less than deadline
    reminder = deadline - datetime.timedelta(days=1)
    reminder_str = reminder.strftime("%Y-%m-%d")
    return {
        "deadline": deadline_str,
        "reminderDate": reminder_str,
    }


@register
@require_kownsl_service
def get_email_details(task: BaseTask) -> dict:
    """
    Get email details required to build the email that is sent from the
    accordeer/adviseer sub processes in Camunda.

    **Required process variables**

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.
    * ``deadline``: deadline of the review request.
    * ``kownslFrontendUrl``: URL that takes you to the review request.

    **Optional process variables**

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    **Sets the process variables**

    * ``email``: a JSON that holds the email content and subject.

      .. code-block:: json

            {
                "subject": "Email subject",
                "content": "Email content",
            }

    * ``context``: a JSON that holds data relevant to the email:

      .. code-block:: json

            {
                "deadline": "2020-12-31",
                "kownslFrontendUrl": "somekownslurl",
                "reminder": True/False,
            }

    * ``template``: a string that determines which template will be used for the email.
    * ``senderUsername``: a list that holds a string of the review requester's username.
      This is used to determine the email's sender's details.
    """
    # Get review request
    review_request = get_review_request(task)

    # Get review request requester
    requester = review_request["requester"]

    # Set template
    template = (
        "accordering" if review_request["review_type"] == "approval" else "advies"
    )

    # Get variables
    variables = task.get_variables()

    # Get kownslFrontendUrl
    kownsl_frontend_url = check_variable(variables, "kownslFrontendUrl")

    # Get deadline
    deadline_str = check_variable(variables, "deadline")

    # Get reminder
    deadline = datetime.datetime.strptime(deadline_str, "%Y-%m-%d")
    reminder = datetime.datetime.now() + datetime.timedelta(days=1) >= deadline

    # Set email process variable
    email = {
        "subject": f"Uw {template} wordt gevraagd",
        "content": "",
    }

    # Set context process variable
    context = {
        "deadline": deadline_str,
        "kownslFrontendUrl": kownsl_frontend_url,
        "reminder": reminder,
    }

    return {
        "email": email,
        "context": context,
        "template": template,
        "senderUsername": [requester],
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
        "reviewrequest",
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
    approvals = client.list("approval", parent_lookup_request__uuid=review_request_id)

    # Get their toelichtingen
    toelichtingen = [approval["toelichting"] or "Geen" for approval in approvals]

    return {"toelichtingen": "\n\n".join(toelichtingen)}
