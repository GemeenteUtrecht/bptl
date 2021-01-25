from uuid import UUID

from django.http import HttpResponse, HttpResponseRedirect

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from rest_framework import permissions, status, views
from rest_framework.request import Request
from rest_framework.response import Response

from bptl.work_units.xential.models import XentialTicket
from bptl.work_units.xential.serializers import TicketUuidSerializer

from .client import get_client


class DocumentCreationCallbackView(views.APIView):
    # TODO
    # authentication_classes =
    # permission_classes = (permissions.IsAuthenticated,)
    # parser_classes = (CamelCaseJSONParser,)

    def post(self, request: Request) -> Response:
        serializer = TicketUuidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bptl_ticket_uuid = serializer.validated_data["bptl_ticket_uuid"]

        # Retrieve the task
        xential_ticket = XentialTicket.objects.get(bptl_ticket_uuid=bptl_ticket_uuid)
        task = xential_ticket.task

        # TODO
        # Retrieve the document from Xential

        # Create the document in the Document API

        # Close task

        return Response(status=status.HTTP_204_NO_CONTENT)


class InteractiveDocumentView(views.APIView):
    # TODO
    # authentication_classes =
    # permission_classes = (permissions.IsAuthenticated,)
    # parser_classes = (CamelCaseJSONParser,)

    def get(self, request: Request, uuid: UUID) -> HttpResponse:
        # With the BPTL specific UUID, we can retrieve the Xential ticket ID
        xential_ticket = XentialTicket.objects.get(bptl_ticket_uuid=uuid)

        xential_client = get_client(xential_ticket.task)

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
        xential_url = response_data["resumeUrl"]

        # Redirect the user to the Xential URL to interactively create a document
        return HttpResponseRedirect(redirect_to=xential_url)
