import base64
import datetime
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.views.generic import RedirectView

from rest_framework import permissions, status, views
from rest_framework.request import Request
from rest_framework.response import Response

from bptl.work_units.xential.models import XentialTicket
from bptl.work_units.xential.serializers import CallbackDataSerializer

from ...tasks.base import check_variable
from .authentication import XentialAuthentication
from .client import DRC_ALIAS, XENTIAL_ALIAS, get_client
from .handlers import on_document_created
from .tokens import token_generator
from .utils import SnakeXMLParser, get_xential_base_url


class DocumentCreationCallbackView(views.APIView):
    authentication_classes = (XentialAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = [SnakeXMLParser]

    def post(self, request: Request) -> Response:
        # The callback sends the base64 encoded document and the BPTL ticket ID as XML.
        serializer = CallbackDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bptl_ticket_uuid = serializer.validated_data["bptl_ticket_uuid"]

        # Retrieve the task
        xential_ticket = XentialTicket.objects.get(bptl_ticket_uuid=bptl_ticket_uuid)
        task = xential_ticket.task

        # Mark the Xential ticket as complete
        xential_ticket.is_ticket_complete = True
        xential_ticket.save()

        # Create the document in the Document API
        variables = task.get_variables()
        document_properties = check_variable(variables, "documentMetadata")
        document_properties.setdefault(
            "creatiedatum", datetime.date.today().strftime("%Y-%m-%d")
        )
        document_properties.setdefault("taal", "nld")
        document_properties["inhoud"] = base64.b64encode(
            serializer.validated_data["document"].read()
        ).decode("utf8")

        drc_client = get_client(task, DRC_ALIAS)
        document = drc_client.post(
            "enkelvoudiginformatieobjecten", json=document_properties
        )

        # Notify camunda that the document has been created
        on_document_created(task, document["url"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class InteractiveDocumentView(RedirectView):
    def get_redirect_url(self, uuid: UUID, token: str, *args, **kwargs) -> str:
        # With the BPTL specific UUID, we can retrieve the Xential ticket ID
        xential_ticket = get_object_or_404(XentialTicket, bptl_ticket_uuid=uuid)

        # Check that the token is valid
        valid = token_generator.check_token(xential_ticket, token)
        if not valid:
            raise PermissionDenied

        xential_client = get_client(xential_ticket.task, XENTIAL_ALIAS)

        # Start document with existing ticket ID
        start_document_url = "document/startDocument"
        response_data = xential_client.post(
            start_document_url,
            params={"ticketUuid": xential_ticket.ticket_uuid},
        )

        xential_base_url = get_xential_base_url(xential_client.api_root)
        xential_url = xential_base_url + response_data["resumeUrl"]

        # Redirect the user to the Xential URL to interactively create a document
        return xential_url
