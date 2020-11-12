import datetime

from zds_client.schema import get_operation_url

from bptl.tasks.base import BaseTask, check_variable
from bptl.tasks.registry import register

from .utils import get_client, get_review_request


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

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.
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
    review_request_id = check_variable(variables, "kownslReviewRequestId")

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

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.
    * ``zaakUrl``: URL reference to the zaak used for the review itself.
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

    review_request_id = review_request["id"]

    # Get review request type to set operation_id
    review_type = review_request["review_type"]
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

    # Get approvals/advices belonging to review request
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

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.
    * ``zaakUrl``: URL reference to the zaak used for the review itself.
    * ``kownslUsers``: list of usernames that have been configured in the review request configuration.

    **Sets the process variables**

    * ``reminderDate``: a string containing the reminder date: "2020-02-29".
    * ``deadline``: a string containing the deadline date: "2020-03-01".
    """
    # Get kownslUsers
    variables = task.get_variables()
    kownsl_users = check_variable(variables, "kownslUsers")

    # Get the review request with id as given in variables
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
def get_email_details(task: BaseTask) -> dict:
    """
    Get email details required to build the email that is sent from the
    accordeer/adviseer sub processes in Camunda.

    **Required process variables**

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.
    * ``zaakUrl``: URL reference to the zaak used for the review itself.
    * ``deadline``: deadline of the review request.
    * ``kownslFrontendUrl``: URL that takes you to the review request.

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

    # Get other variables
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
def get_approval_toelichtingen(task: BaseTask) -> dict:
    """
    Get the "toelichtingen" of all reviewers that responded to the review request.

    **Required process variables**

    * ``kownslReviewRequestId``: the identifier of the Kownsl review request.
    * ``zaakUrl``: URL reference to the zaak used for the review itself.

    **Sets the process variables**

    * ``toelichtingen``: a string containing the "toelichtingen" of all reviewers.
    """

    # Get the review request with id as given in variables
    review_request = get_review_request(task)
    review_request_id = review_request["id"]
    operation_id = "reviewrequest_approvals"
    client = get_client(task)
    url = get_operation_url(
        client.schema,
        operation_id,
        base_url=client.base_url,
        uuid=review_request_id,
    )

    # Get approvals belonging to review request
    approvals = client.request(url, operation_id)

    # Get their toelichtingen
    toelichtingen = []
    for approval in approvals:
        toelichtingen.append(
            "Accordeur: {author}\nToelichting: {toelichting}".format(
                author=approval["author"], toelichting=approval["toelichting"]
            )
        )

    return {"toelichtingen": "\n\n".join(toelichtingen)}
