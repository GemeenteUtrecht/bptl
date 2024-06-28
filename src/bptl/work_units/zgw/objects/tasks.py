import datetime
import logging
from typing import Dict

from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes

from bptl.tasks.base import BaseTask, MissingVariable, check_variable
from bptl.tasks.registry import register
from bptl.work_units.zgw.tasks.base import ZGWWorkUnit, require_zrc, require_ztc

from .client import require_objects_service, require_objecttypes_service
from .services import (
    create_object,
    fetch_checklist,
    fetch_checklist_objecttype,
    fetch_checklisttype,
    get_review_request,
    get_reviews_for_review_request,
    update_review_request,
)

logger = logging.getLogger(__name__)


###################################################
#                   Checklists                    #
###################################################


@register
@require_objects_service
@require_objecttypes_service
@require_zrc
@require_ztc
class InitializeChecklistTask(ZGWWorkUnit):
    """
    Creates an empty CHECKLIST for ZAAK if CHECKLISTTYPE for ZAAKTYPE exists.

    **Required process variables**
    * ``zaakUrl`` [str]: URL-reference of the ZAAK in Open Zaak.
    * ``catalogusDomein`` [str]: `domein` of the CATALOGUS in Open Zaak OR ``zaaktypeCatalogus`` [str]: URL-reference of CATALOGUS in CATALOGUS of Open Zaak.
    * ``zaaktypeIdentificatie`` [str]: URL-reference of ZAAKTYPE in CATALOGUS of Open Zaak.

    **Sets the process variables**

    * ``initializedChecklist`` [bool]: Boolean that indicates whether an empty checklist was created.

    """

    def check_if_checklisttype_does_not_exist(self, variables: Dict) -> bool:
        # Check if checklisttype exists
        catalogus_domein = variables.get("catalogusDomein", None)
        if not catalogus_domein:
            catalogus_url = variables.get("zaaktypeCatalogus", None)
            if catalogus_url:
                ztc_client = self.get_client(APITypes.ztc)
                catalogus = ztc_client.retrieve("catalogus", url=catalogus_url)
                catalogus_domein = catalogus.get("domein", None)

        if not catalogus_domein:
            raise MissingVariable(
                "The variables `catalogusDomein` and `zaaktypeCatalogus` are missing or empty. Please supply either one."
            )

        zaaktype_identificatie = check_variable(variables, "zaaktypeIdentificatie")
        checklisttype = fetch_checklisttype(
            self.task, catalogus_domein, zaaktype_identificatie
        )
        if not checklisttype:
            logger.warning(
                "CHECKLISTTYPE not found for ZAAKTYPE with identificatie: `{ztid}` in CATALOGUS with domein: `{domein}`.".format(
                    ztid=zaaktype_identificatie, domein=catalogus_domein
                )
            )
            return True
        return False

    def check_if_checklist_exists(self, variables: Dict) -> bool:
        # Check if checklist already exists
        zaak_url = check_variable(variables, "zaakUrl")
        checklist = fetch_checklist(self.task, zaak_url)
        if checklist:
            logger.warning("CHECKLIST already exists for ZAAK.")
            return True
        return False

    def perform(self) -> dict:
        variables = self.task.get_variables()
        with parallel() as executor:
            checks = list(
                executor.map(
                    lambda func: func(variables),
                    [
                        self.check_if_checklisttype_does_not_exist,
                        self.check_if_checklist_exists,
                    ],
                )
            )
        if any(checks):
            return {"initializedChecklist": False}

        zaak_url = check_variable(variables, "zaakUrl")
        latest_version = fetch_checklist_objecttype(self.task)
        record = {
            "answers": [],
            "zaak": zaak_url,
            "locked": False,
        }
        data = {
            "type": latest_version["objectType"],
            "record": {
                "typeVersion": latest_version["version"],
                "data": record,
                "startAt": datetime.date.today().isoformat(),
            },
        }
        obj = create_object(self.task, data)
        relation_data = {
            "zaak": zaak_url,
            "object": obj["url"],
            "object_type": "overige",
            "object_type_overige": latest_version["jsonSchema"]["title"],
            "object_type_overige_definitie": {
                "url": latest_version["url"],
                "schema": ".jsonSchema",
                "objectData": ".record.data",
            },
            "relatieomschrijving": "Checklist van Zaak",
        }
        client = self.get_client(APITypes.zrc)
        client.create("zaakobject", relation_data)
        return {"initializedChecklist": True}


###################################################
#            KOWNSL - review requests             #
###################################################


@register
@require_objects_service
@require_objecttypes_service
def get_approval_status(task: BaseTask) -> dict:
    """
    Get the result of an approval review request.

    Once all reviewers have submitted their approval or rejection, derive the end-result
    from the review session. If all reviewers approve, the result is positive. If any
    rejections are present, the result is negative.

    In the task binding, the service with alias ``kownsl`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``kownslReviewRequestId`` [str]: the identifier of the Kownsl review request.

    **Sets the process variables**

    * ``approvalResult`` [bool]: a boolean indication approval status.

    """

    reviews = get_reviews_for_review_request(task)

    num_approved, num_rejected = 0, 0
    if reviews:
        for rev in reviews.get("reviews", []):
            if rev.get("approved", None):
                num_approved += 1
            else:
                num_rejected += 1

    return {"approvalResult": num_approved > 0 and num_rejected == 0}


@register
@require_objects_service
@require_objecttypes_service
def get_review_response_status(task: BaseTask) -> dict:
    """
    Get the reviewers who have not yet responded to a review request so that
    a reminder email can be sent to them if they exist.

    In the task binding, the service with alias ``kownsl`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``kownslReviewRequestId`` [str]: the identifier of the Kownsl review request.
    * ``kownslUsers`` [list[str]]: list of users or groups that have been configured in the review request configuration.

    **Sets the process variables**

    * ``remindThese`` [list[str]]: a JSON-object containing a list of users or groups who need reminding:

      .. code-block:: json

            [
                "user:user1",
                "user:user2",
            ]
    """
    # Check who should respond
    variables = task.get_variables()
    needs_to_respond = check_variable(variables, "kownslUsers")

    # Get approvals/advices belonging to review request
    reviews = get_reviews_for_review_request(task)

    # Build a list of users that have responded
    already_responded = []
    if reviews:
        for review in reviews.get("reviews", []):
            user = (
                f"group:{review['group']}"
                if review.get("group", None)
                else f"user:{review['author']['username']}"
            )
            already_responded.append(user)

    # Finally figure out who hasn't responded yet
    not_responded = [
        username for username in needs_to_respond if username not in already_responded
    ]
    return {
        "remindThese": not_responded,
    }


@register
@require_objects_service
@require_objecttypes_service
def get_review_request_start_process_information(task: BaseTask) -> dict:
    """
    Get the process information for the review request.
    The process information consists of the:

    - deadline of the review request,
    - reminder date of the review request,
    - lock status of the review request,
    - the username of the requester,
    - and finally, the review type.

    In the task binding, the service with alias ``kownsl`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``kownslReviewRequestId`` [str]: the identifier of the Kownsl review request.
    * ``kownslUsers`` [list[str]]: list of usernames that have been configured in the review request configuration.

    **Sets the process variables**

    * ``reminderDate`` [str]: the email reminder date: "2020-02-29".
    * ``deadline`` [str]: the review deadline date: "2020-03-01".
    * ``locked`` [bool]: the lock status of the review request.
    * ``requester`` [str]: the username of the review requester.
    * ``reviewType`` [str]: the review type (i.e., "advice" or "approval").

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
        "requester": f"user:{review_request['requester']['username']}",
        "reviewType": (
            "advies" if review_request["reviewType"] == "advice" else "accordering"
        ),
    }


@register
@require_objects_service
@require_objecttypes_service
def set_review_request_metadata(task: BaseTask) -> dict:
    """
    Set the metadata for a Kownsl review request.

    Metadata is a set of arbitrary key-value labels, allowing you to attach extra data
    required for your process routing/handling.

    **Required process variables**

    * ``kownslReviewRequestId`` [str]: the identifier of the Kownsl review request.
    * ``metadata`` [json]: a JSON structure holding key-values of the metadata. This will be
      set directly on the matching review request. Example:

      .. code-block:: json

            {
                "processInstanceId": "aProcessInstanceId"
            }

    **Sets no process variables**

    """
    variables = task.get_variables()
    metadata = check_variable(variables, "metadata")
    data = {"metadata": metadata}
    update_review_request(task, requester=None, data=data)
    return dict()


@register
@require_objects_service
@require_objecttypes_service
def get_approval_toelichtingen(task: BaseTask) -> dict:
    """
    Get the "toelichtingen" of all reviewers that responded to the review request.

    **Required process variables**

    * ``kownslReviewRequestId`` [str]: the identifier of the Kownsl review request.

    **Sets the process variables**

    * ``toelichtingen`` [str]: the "toelichtingen" of all reviewers.

    """
    # Get approvals/advices belonging to review request
    reviews = get_reviews_for_review_request(task)

    toelichtingen = []
    if reviews:
        # Get their toelichtingen
        toelichtingen = (
            [rev.get("toelichting", None) or "Geen" for rev in reviews["reviews"]]
            if reviews.get("reviews", None)
            else []
        )

    return {"toelichtingen": "\n\n".join(toelichtingen)}


@register
@require_objects_service
@require_objecttypes_service
def lock_review_request(task: BaseTask) -> dict:
    """
    Lock review request after all reviews have been given.

    **Required process variables**

    * ``kownslReviewRequestId`` [str]: the identifier of the Kownsl review request.

    **Sets no process variables**

    """
    data = {"locked": True, "lock_reason": "Alle verzoeken zijn uitgevoerd."}
    update_review_request(task, requester=None, data=data)
    return dict()
