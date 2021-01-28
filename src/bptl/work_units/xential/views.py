from urllib.parse import urlparse
from uuid import UUID

from django.http import HttpResponse, HttpResponseRedirect
from django.views import View

from defusedxml import minidom
from rest_framework import status, views
from rest_framework.request import Request
from rest_framework.response import Response

from bptl.work_units.xential.models import XentialTicket
from bptl.work_units.xential.serializers import CallbackDataSerializer

from ...tasks.base import check_variable
from .client import DRC_ALIAS, XENTIAL_ALIAS, get_client
from .handlers import on_document_created


def parse_xml(raw_xml: str) -> dict:
    parsed_xml = minidom.parseString(raw_xml)  # minidom from defusedxml
    extracted_data = {}

    document_node = parsed_xml.getElementsByTagName("document")
    extracted_data["document"] = document_node[0].firstChild.nodeValue

    ticket_node = parsed_xml.getElementsByTagName("bptlTicketUuid")
    extracted_data["bptl_ticket_id"] = ticket_node[0].firstChild.nodeValue

    return extracted_data


class DocumentCreationCallbackView(views.APIView):
    def post(self, request: Request) -> Response:
        # The callback sends the base64 encoded document and the BPTL ticket ID as XML.
        callback_data = parse_xml(request.data)

        serializer = CallbackDataSerializer(data=callback_data)
        serializer.is_valid(raise_exception=True)

        bptl_ticket_uuid = serializer.validated_data["bptl_ticket_uuid"]

        # Retrieve the task
        xential_ticket = XentialTicket.objects.get(bptl_ticket_uuid=bptl_ticket_uuid)
        task = xential_ticket.task

        # Create the document in the Document API
        variables = task.get_variables()
        document_properties = check_variable(variables, "documentMetadata")
        document_properties["inhoud"] = serializer.validated_data["document"]

        drc_client = get_client(task, DRC_ALIAS)
        drc_client.post("/enkelvoudiginformatieobjecten", json=document_properties)

        # Notify camunda that the document has been created
        on_document_created(task)

        return Response(status=status.HTTP_204_NO_CONTENT)


class InteractiveDocumentView(View):
    def get(self, request: Request, uuid: UUID) -> HttpResponse:
        # With the BPTL specific UUID, we can retrieve the Xential ticket ID
        xential_ticket = XentialTicket.objects.get(bptl_ticket_uuid=uuid)

        xential_client = get_client(xential_ticket.task, XENTIAL_ALIAS)

        # Step 1: Retrieve XSessionID
        xsession_id_url = "auth/whoami"
        response_data = xential_client.post(xsession_id_url)
        headers = {"Cookie": f"XSessionID={response_data['XSessionId']}"}

        # Step 2: Start document with existing ticket ID
        start_document_url = "document/startDocument"
        response_data = xential_client.post(
            start_document_url,
            headers=headers,
            params={"ticketUuid": xential_ticket.ticket_uuid},
        )

        xential_base_url = get_xential_base_url(xential_client.api_root)
        xential_url = xential_base_url + response_data["resumeUrl"]

        # Redirect the user to the Xential URL to interactively create a document
        return HttpResponseRedirect(redirect_to=xential_url)


def get_xential_base_url(api_root: str) -> str:
    parsed_url = urlparse(api_root)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"
