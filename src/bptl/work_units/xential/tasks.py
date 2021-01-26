import json
import uuid
from xml.dom import minidom

from django.conf import settings
from django.contrib.sites.models import Site

from rest_framework.reverse import reverse

from bptl.tasks.base import BaseTask, check_variable
from bptl.tasks.registry import register

from .client import get_client, require_xential_service
from .models import XentialTicket


@register
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
    * ``interactive``: True or False, whether the process will be interactive or not
    * ``templateVariables``: a JSON-object containing meta-data about the result:

      .. code-block:: json

         {
            "variable1": "String",
            "variable2": "String"
         }

    **Sets the process variable**

    * ``bptlDocumentUrl``: BPTL specific URL for interactive documents. If the document creation is not interactive, this will be empty.

    """
    variables = task.get_variables()
    interactive = check_variable(variables, "interactive")
    template_uuid = check_variable(variables, "templateUuid")
    template_variables = check_variable(variables, "templateVariables")
    xential_client = get_client(task)

    # Step 1: Retrieve XSessionID
    xsession_id_url = "auth/whoami"
    response_data = xential_client.post(xsession_id_url)
    headers = {"Cookie": f"XSessionID={response_data['XSessionId']}"}

    # Step 2: Create a ticket
    create_ticket_url = "createTicket"

    # Make a bptl ID for this ticket, so that later the task can be completed
    bptl_ticket_uuid = str(uuid.uuid4())

    # The option parameter needs *all* fields filled (even if empty), otherwise
    # a 500 response is given.
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
                        "headers": [],
                        "contentType": "application/json",
                        "requestBody": f'<data xmlns:sup="nl.inext.statusupdates"><document><sup:param name="documentData"/></document><bptlTicketUuid>{bptl_ticket_uuid}</bptlTicketUuid></data>',
                        "clientCertificateId": "xentiallabs",
                    },
                }
            ]
        },
    }
    # Ticket data contains the template variables formatted as XML to fill the document
    ticket_data = make_xml_from_template_variables(template_variables)

    response_data = xential_client.post(
        create_ticket_url,
        headers=headers,
        files={
            "options": ("options", json.dumps(options), "application/json"),
            "ticketData": ("ticketData", ticket_data, "text/xml"),
        },
    )
    ticket_uuid = response_data["ticketId"]

    XentialTicket.objects.create(
        task=task,
        bptl_ticket_uuid=bptl_ticket_uuid,
        ticket_uuid=ticket_uuid,
    )

    if interactive == "False":
        # Step 3: Start a document
        start_document_url = "document/startDocument"
        response_data = xential_client.post(
            start_document_url, headers=headers, params={"ticketUuid": ticket_uuid}
        )
        document_uuid = response_data["documentUuid"]

        # Step 4: Build document silently
        # Once the document is created, Xential will notify the DocumentCreationCallbackView.
        # If not all template variables are filled, building the document will not work.
        build_document_url = "document/buildDocument"
        params = {"documentUuid": document_uuid}
        xential_client.post(build_document_url, params=params, headers=headers)

        return {"bptlDocumentUrl": ""}

    interactive_document_path = reverse(
        "Xential:interactive-document", args=[bptl_ticket_uuid]
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
