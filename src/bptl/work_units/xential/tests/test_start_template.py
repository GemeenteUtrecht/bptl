from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.camunda.models import ExternalTask
from bptl.tasks.models import TaskMapping
from bptl.tasks.tests.factories import DefaultServiceFactory

from ..models import XentialTicket
from ..tasks import start_xential_template

XENTIAL_API_ROOT = "https://xentiallabs.com/xential/modpages/next.oas/api/"
DRC_ROOT = "https://openzaak.nl/documenten/api/v1/"


@requests_mock.Mocker()
class XentialTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMapping.objects.create(
            topic_name="xential-topic",
        )

        xential = Service.objects.create(
            label="xential",
            api_type=APITypes.orc,
            api_root=XENTIAL_API_ROOT,
            auth_type=AuthTypes.api_key,
            oas="",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service=xential,
            alias="xential",
        )

        drc = Service.objects.create(
            label="Documenten API",
            api_type=APITypes.drc,
            api_root=DRC_ROOT,
            auth_type=AuthTypes.api_key,
            oas="",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service=drc,
            alias="drc",
        )

    def test_start_silent_template(self, m):
        m.post(
            f"{XENTIAL_API_ROOT}auth/whoami",
            json={
                "user": {
                    "uuid": "a4664ccb-259e-4107-b800-d8e5a764b9dd",
                    "userName": "testuser",
                },
                "XSessionId": "f7f588eb-b7c9-4d23-babd-4a98a9326367",
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}createTicket",
            json={"ticketId": "b0fdd542-0cc4-44a1-8dfb-808436123ce8"},
        )
        m.post(
            f"{XENTIAL_API_ROOT}document/startDocument?ticketUuid=b0fdd542-0cc4-44a1-8dfb-808436123ce8",
            json={
                "documentUuid": "527f6ea1-e292-41ec-ac5b-8f8feddf153f",
                "resumeUrl": "/xential?resumeApplication=527f6ea1-e292-41ec-ac5b-8f8feddf153f&loginTicketUuid=4c68ae87-1e13-49db-8744-600a4c86a067",
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}document/buildDocument?documentUuid=527f6ea1-e292-41ec-ac5b-8f8feddf153f",
            json={"success": True},
        )

        external_task = ExternalTask.objects.create(
            topic_name="xential-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "bptlAppId": serialize_variable("some-app-id"),
                "templateUuid": serialize_variable(
                    "3e09b238-0617-47c1-8e6a-f6227b3d542e"
                ),
                "interactive": serialize_variable(False),
                "templateVariables": serialize_variable(
                    {"textq1": "Answer1", "dateq1": "31-12-20"}
                ),
                "documentMetadata": serialize_variable(
                    {
                        "bronorganisatie": "517439943",
                        "creatiedatum": "01-01-2021",
                        "titel": "Test Document",
                        "auteur": "Test Author",
                        "taal": "eng",
                        "informatieobjecttype": "http://openzaak.nl/catalogi/api/v1/informatieobjecttypen/06d3a135-bc20-4fce-9add-f69d8e585917",
                    }
                ),
            },
        )

        result = start_xential_template(external_task)

        self.assertEqual(result, {"bptlDocumentUrl": ""})

        # Check that the XentialTicket object was created
        xential_ticket = XentialTicket.objects.get()

        self.assertEqual(
            "b0fdd542-0cc4-44a1-8dfb-808436123ce8", str(xential_ticket.ticket_uuid)
        )

    def test_start_interactive_template(self, m):
        m.post(
            f"{XENTIAL_API_ROOT}auth/whoami",
            json={
                "user": {
                    "uuid": "a4664ccb-259e-4107-b800-d8e5a764b9dd",
                    "userName": "testuser",
                },
                "XSessionId": "f7f588eb-b7c9-4d23-babd-4a98a9326367",
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}createTicket",
            json={"ticketId": "b0fdd542-0cc4-44a1-8dfb-808436123ce8"},
        )

        external_task = ExternalTask.objects.create(
            topic_name="xential-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "bptlAppId": serialize_variable("some-app-id"),
                "templateUuid": serialize_variable(
                    "3e09b238-0617-47c1-8e6a-f6227b3d542e"
                ),
                "interactive": serialize_variable(True),
                "templateVariables": serialize_variable(
                    {"textq1": "Answer1", "dateq1": "31-12-20"}
                ),
                "documentMetadata": serialize_variable(
                    {
                        "bronorganisatie": "517439943",
                        "creatiedatum": "01-01-2021",
                        "titel": "Test Document",
                        "auteur": "Test Author",
                        "taal": "eng",
                        "informatieobjecttype": "http://openzaak.nl/catalogi/api/v1/informatieobjecttypen/06d3a135-bc20-4fce-9add-f69d8e585917",
                    }
                ),
            },
        )

        result = start_xential_template(external_task)

        # Check that the XentialTicket object was created
        xential_ticket = XentialTicket.objects.get()
        bptl_ticket_url = f"https://example.com/contrib/api/xential/interactive_document/{xential_ticket.bptl_ticket_uuid}"

        self.assertEqual(
            "b0fdd542-0cc4-44a1-8dfb-808436123ce8", str(xential_ticket.ticket_uuid)
        )
        self.assertEqual(bptl_ticket_url, result["bptlDocumentUrl"])
