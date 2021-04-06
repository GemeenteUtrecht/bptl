import json
import uuid
from xml.dom import minidom

from django.conf import settings
from django.contrib.sites.models import Site

from celery.utils.log import get_task_logger
from rest_framework.reverse import reverse

from bptl.tasks.base import BaseTask, check_variable
from bptl.tasks.registry import register

from ...camunda.utils import fail_task
from ...celery import app
from .client import (
    XENTIAL_ALIAS,
    get_client,
    require_drc_service,
    require_xential_service,
)
from .models import XentialConfiguration, XentialTicket
from .tokens import token_generator
from .utils import check_document_api_required_fields

logger = get_task_logger(__name__)


@register
@require_drc_service
@require_xential_service
def start_xential_template(task: BaseTask) -> dict:
    """
    Run Xential template with requested variables.
    If the ``interactive`` task variable is:
    * ``True``: it returns a URL in ``bptlDocumentUrl`` for building a document interactively
    * ``False``: it returns an empty string in ``bptlDocumentUrl``

    In the task binding, the service with alias ``xential`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``bptlAppId``: the application ID in the BPTL credential store
    * ``templateUuid``: the id of the template which should be started
    * ``interactive``: bool, whether the process will be interactive or not
    * ``templateVariables``: a JSON-object containing the data to fill the template. In an interactive flow, this can be
        an empty object ``{}``:

      .. code-block:: json

         {
            "variable1": "String",
            "variable2": "String"
         }

    * ``documentMetadata``: a JSON-object containing the fields required to create a document in the Documenten API.
        The fields shown below are required. The property 'creatiedatum' defaults to the day in which the document is
        sent to the Documenten API and the property 'taal' defaults to 'nld' (dutch).

      .. code-block:: json

         {
            "bronorganisatie": "string",
            "titel": "string",
            "auteur": "string",
            "informatieobjecttype": "url"
         }

    **Optional process variable**

    * ``messageId``: string. The message ID to send back into the process when the
    document is sent to the Documenten API. You can use this to continue process execution.
    If left empty, then no message will be sent.

    **Sets the process variable**

    * ``bptlDocumentUrl``: BPTL specific URL for interactive documents.
        If the document creation is not interactive, this will be empty.

    """
    variables = task.get_variables()
    interactive = check_variable(variables, "interactive")
    template_uuid = check_variable(variables, "templateUuid")
    template_variables = check_variable(
        variables, "templateVariables", empty_allowed=True
    )
    xential_client = get_client(task, XENTIAL_ALIAS)

    check_document_api_required_fields(check_variable(variables, "documentMetadata"))

    # Step 1: Create a ticket
    create_ticket_url = "createTicket"

    # Make a bptl UUID for this ticket, so that later the task can be retrieved
    bptl_ticket_uuid = str(uuid.uuid4())

    # The `options` parameter needs *all* fields filled (even if empty), otherwise
    # a 500 response is given.
    config = XentialConfiguration.get_solo()
    options = {
        "printOption": {},
        "mailOption": {},
        "documentPropertiesOption": {},
        "valuesOption": {},
        "attachmentsOption": {},
        "ttlOption": {},
        "selectionOption": {"templateUuid": template_uuid},
        "webhooksOption": {
            "hooks": [
                {
                    "event": "document.built",
                    "retries": {"count": 0, "delayMs": 0},
                    "request": {
                        "url": get_absolute_url(reverse("Xential:xential-callbacks")),
                        "method": "POST",
                        "contentType": "application/xml",
                        "headers": [
                            {
                                "name": "Authorization",
                                "value": f"Basic {config.auth_key}",
                            }
                        ],
                        "requestBody": f'<data xmlns:sup="nl.inext.statusupdates"><document><sup:param name="documentData"/></document><bptlTicketUuid>{bptl_ticket_uuid}</bptlTicketUuid></data>',
                    },
                }
            ]
        },
    }
    # `ticket_data` contains the template variables formatted as XML to fill the document
    ticket_data = make_xml_from_template_variables(template_variables)

    response_data = xential_client.post(
        create_ticket_url,
        files={
            "options": ("options", json.dumps(options), "application/json"),
            "ticketData": ("ticketData", ticket_data, "text/xml"),
        },
    )
    ticket_uuid = response_data["ticketId"]

    ticket = XentialTicket.objects.create(
        task=task,
        bptl_ticket_uuid=bptl_ticket_uuid,
        ticket_uuid=ticket_uuid,
        is_ticket_complete=False,
    )

    if not interactive:
        # Step 2: Start a document
        start_document_url = "document/startDocument"
        response_data = xential_client.post(
            start_document_url, params={"ticketUuid": ticket_uuid}
        )
        document_uuid = response_data["documentUuid"]

        # Step 3: Build document silently
        # If not all template variables are filled, building the document will not work.
        build_document_url = "document/buildDocument"
        params = {"documentUuid": document_uuid, "close": "true"}
        xential_client.post(build_document_url, params=params)

        ticket.document_uuid = document_uuid
        ticket.save()

        return {"bptlDocumentUrl": ""}

    token = token_generator.make_token(ticket)
    interactive_document_path = reverse(
        "Xential:interactive-document", args=[bptl_ticket_uuid, token]
    )

    return {"bptlDocumentUrl": get_absolute_url(interactive_document_path)}


def get_absolute_url(path: str) -> str:
    site = Site.objects.get_current()
    protocol = "https" if settings.IS_HTTPS else "http"
    return f"{protocol}://{site.domain}{path}"


def make_xml_from_template_variables(template_variables: dict) -> str:
    xml_doc = minidom.Document()
    root_element = xml_doc.createElement("root")

    for variable_name, variable_value in template_variables.items():
        xml_tag = xml_doc.createElement(variable_name)
        xml_text = xml_doc.createTextNode(variable_value)
        xml_tag.appendChild(xml_text)
        root_element.appendChild(xml_tag)

    xml_doc.appendChild(root_element)
    return xml_doc.toxml()


@app.task
def check_failed_document_builds():
    logger.debug("Checking for failed Xential document builds")

    # Getting all incomplete tickets with an associated document ID
    open_tickets = XentialTicket.objects.filter(
        is_ticket_complete=False, document_uuid__isnull=False
    )

    for ticket in open_tickets:
        check_xential_document_status.delay(str(ticket.bptl_ticket_uuid))


@app.task
def check_xential_document_status(ticket_uuid: str) -> None:
    xential_ticket = XentialTicket.objects.get(bptl_ticket_uuid=ticket_uuid)
    task = xential_ticket.task
    xential_client = get_client(task, XENTIAL_ALIAS)

    # Request the status of the document to Xential
    document_data = xential_client.get(f"document/{xential_ticket.document_uuid}")

    # If no error has occurred, then there is nothing to do
    if document_data["buildStatus"] != "ERROR":
        return

    fail_task(task, reason="Xential failed to build the document.")
