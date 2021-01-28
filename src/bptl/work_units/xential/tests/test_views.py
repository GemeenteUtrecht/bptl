import os

from django.test import TestCase
from django.urls import reverse_lazy

import requests_mock
from django_camunda.utils import serialize_variable
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.camunda.models import ExternalTask
from bptl.tasks.models import TaskMapping
from bptl.tasks.tests.factories import DefaultServiceFactory
from bptl.work_units.xential.models import XentialTicket
from bptl.work_units.xential.tasks import get_absolute_url

XENTIAL_API_ROOT = "https://xentiallabs.com/xential/modpages/next.oas/api/"
DRC_ROOT = "https://openzaak.nl/documenten/api/v1/"


@requests_mock.Mocker()
class InteractiveDocumentUrlViewTest(TestCase):
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

    def test_interactive_document_redirect(self, m):
        bptl_ticket_uuid = "f7f588eb-b7c9-4d23-babd-4a98a9326367"
        ticket_uuid = "99e6189a-e081-448b-a280-ca5bcde21d4e"

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
            f"{XENTIAL_API_ROOT}document/startDocument?ticketUuid={ticket_uuid}",
            json={
                "documentUuid": "527f6ea1-e292-41ec-ac5b-8f8feddf153f",
                "resumeUrl": "/xential?resumeApplication=527f6ea1-e292-41ec-ac5b-8f8feddf153f&loginTicketUuid=4c68ae87-1e13-49db-8744-600a4c86a067",
            },
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
                "interactive": serialize_variable("True"),
                "templateVariables": serialize_variable({}),
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

        XentialTicket.objects.create(
            task=external_task,
            bptl_ticket_uuid=bptl_ticket_uuid,
            ticket_uuid=ticket_uuid,
        )

        path = reverse("Xential:interactive-document", args=[bptl_ticket_uuid])
        bptl_interactive_url = get_absolute_url(path)

        response = self.client.get(bptl_interactive_url)
        self.assertEqual(status.HTTP_302_FOUND, response.status_code)

        expected_url = "https://xentiallabs.com/xential?resumeApplication=527f6ea1-e292-41ec-ac5b-8f8feddf153f&loginTicketUuid=4c68ae87-1e13-49db-8744-600a4c86a067"
        self.assertEqual(expected_url, response.url)


@requests_mock.Mocker()
class XentialCallbackTest(APITestCase):

    endpoint = reverse_lazy("Xential:xential-callbacks")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

    def _get_sample_response(self, filename: str) -> str:
        file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "responses"
        )
        f = open(os.path.join(file_path, filename), "r")
        response = f.read()
        f.close()

        return response

    def test_callback_no_message_id(self, m):
        xential_response = self._get_sample_response("xential-response.xml")

        bptl_ticket_uuid = "9c132492-6c7c-4c34-af9d-16322dff89cc"
        ticket_uuid = "2d30f19b-8666-4f45-a8da-78ad7ed0ef4d"

        # Setting up DRC service
        mapping = TaskMapping.objects.create(
            topic_name="xential-topic",
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
            alias="DRC",
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
                "interactive": serialize_variable("False"),
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

        # Mock calls
        m.post(
            "https://openzaak.nl/documenten/api/v1/enkelvoudiginformatieobjecten",
            json={
                "identificatie": "DOCUMENT-0001",
                "url": "https://openzaak.nl/documenten/api/v1/enkelvoudiginformatieobjecten/15f4c2e8-f900-4fd1-8f31-44163d369c93",
                "bronorganisatie": "517439943",
                "creatiedatum": "01-01-2021",
                "titel": "Test Document",
                "auteur": "Test Author",
                "taal": "eng",
                "informatieobjecttype": "http://openzaak.nl/catalogi/api/v1/informatieobjecttypen/06d3a135-bc20-4fce-9add-f69d8e585917",
            },
        )

        XentialTicket.objects.create(
            task=external_task,
            bptl_ticket_uuid=bptl_ticket_uuid,
            ticket_uuid=ticket_uuid,
        )

        callback_response = self.client.post(self.endpoint, data=xential_response)

        self.assertEqual(status.HTTP_204_NO_CONTENT, callback_response.status_code)

    def test_callback_with_message_id_no_instance_id(self, m):
        xential_response = self._get_sample_response("xential-response.xml")

        bptl_ticket_uuid = "9c132492-6c7c-4c34-af9d-16322dff89cc"
        ticket_uuid = "2d30f19b-8666-4f45-a8da-78ad7ed0ef4d"

        # Setting up DRC service
        mapping = TaskMapping.objects.create(
            topic_name="xential-topic",
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
            alias="DRC",
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
                "interactive": serialize_variable("False"),
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
                "messageId": serialize_variable("document-created"),
            },
        )

        # Mock calls
        m.post(
            "https://openzaak.nl/documenten/api/v1/enkelvoudiginformatieobjecten",
            json={
                "identificatie": "DOCUMENT-0001",
                "url": "https://openzaak.nl/documenten/api/v1/enkelvoudiginformatieobjecten/15f4c2e8-f900-4fd1-8f31-44163d369c93",
                "bronorganisatie": "517439943",
                "creatiedatum": "01-01-2021",
                "titel": "Test Document",
                "auteur": "Test Author",
                "taal": "eng",
                "informatieobjecttype": "http://openzaak.nl/catalogi/api/v1/informatieobjecttypen/06d3a135-bc20-4fce-9add-f69d8e585917",
            },
        )
        m.get(
            "https://camunda.example.com/engine-rest/history/external-task-log/test-task-id",
            json={"processInstanceId": "some-instance-id"},
        )
        m.post("https://camunda.example.com/engine-rest/message")

        XentialTicket.objects.create(
            task=external_task,
            bptl_ticket_uuid=bptl_ticket_uuid,
            ticket_uuid=ticket_uuid,
        )

        callback_response = self.client.post(self.endpoint, data=xential_response)

        self.assertEqual(status.HTTP_204_NO_CONTENT, callback_response.status_code)

    def test_callback_with_message_id_with_instance_id(self, m):
        xential_response = self._get_sample_response("xential-response.xml")

        bptl_ticket_uuid = "9c132492-6c7c-4c34-af9d-16322dff89cc"
        ticket_uuid = "2d30f19b-8666-4f45-a8da-78ad7ed0ef4d"

        # Setting up DRC service
        mapping = TaskMapping.objects.create(
            topic_name="xential-topic",
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
            alias="DRC",
        )

        external_task = ExternalTask.objects.create(
            topic_name="xential-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            instance_id="test-instance-id",
            variables={
                "bptlAppId": serialize_variable("some-app-id"),
                "templateUuid": serialize_variable(
                    "3e09b238-0617-47c1-8e6a-f6227b3d542e"
                ),
                "interactive": serialize_variable("False"),
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
                "messageId": serialize_variable("document-created"),
            },
        )

        # Mock calls
        m.post(
            "https://openzaak.nl/documenten/api/v1/enkelvoudiginformatieobjecten",
            json={
                "identificatie": "DOCUMENT-0001",
                "url": "https://openzaak.nl/documenten/api/v1/enkelvoudiginformatieobjecten/15f4c2e8-f900-4fd1-8f31-44163d369c93",
                "bronorganisatie": "517439943",
                "creatiedatum": "01-01-2021",
                "titel": "Test Document",
                "auteur": "Test Author",
                "taal": "eng",
                "informatieobjecttype": "http://openzaak.nl/catalogi/api/v1/informatieobjecttypen/06d3a135-bc20-4fce-9add-f69d8e585917",
            },
        )
        m.post("https://camunda.example.com/engine-rest/message")

        XentialTicket.objects.create(
            task=external_task,
            bptl_ticket_uuid=bptl_ticket_uuid,
            ticket_uuid=ticket_uuid,
        )

        callback_response = self.client.post(self.endpoint, data=xential_response)

        self.assertEqual(status.HTTP_204_NO_CONTENT, callback_response.status_code)

    def test_callback_document_not_b64(self, m):
        xential_response = self._get_sample_response("xential-wrong-doc.xml")

        callback_response = self.client.post(self.endpoint, data=xential_response)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, callback_response.status_code)
        self.assertIn("document", callback_response.data)
        self.assertEqual(
            "Non-base64 digit found", callback_response.data["document"][0]
        )
