import requests_mock
from django_camunda.utils import serialize_variable
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.accounts.tests.factories import UserFactory
from bptl.camunda.models import ExternalTask
from bptl.tasks.models import TaskMapping
from bptl.tasks.tests.factories import DefaultServiceFactory
from bptl.work_units.xential.models import XentialTicket
from bptl.work_units.xential.tasks import get_absolute_url

XENTIAL_API_ROOT = "https://xentiallabs.com/xential/modpages/next.oas/api/"
DRC_ROOT = "https://openzaak.nl/documenten/api/v1/"


@requests_mock.Mocker()
class InteractiveDocumentUrlViewTest(APITestCase):
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

    def test_cant_access_interactive_document_url_if_unauthenticated(self, m):
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

        XentialTicket.objects.create(
            task=external_task,
            bptl_ticket_uuid="f7f588eb-b7c9-4d23-babd-4a98a9326367",
            ticket_uuid="99e6189a-e081-448b-a280-ca5bcde21d4e",
        )

        path = reverse(
            "Xential:interactive-document",
            args=["f7f588eb-b7c9-4d23-babd-4a98a9326367"],
        )
        bptl_interactive_url = get_absolute_url(path)

        user = UserFactory.create()
        # self.client.force_authenticate(user=user)
        response = self.client.get(bptl_interactive_url)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

    def test_can_access_interactive_document_url_if_authenticated(self, m):
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

        XentialTicket.objects.create(
            task=external_task,
            bptl_ticket_uuid=bptl_ticket_uuid,
            ticket_uuid=ticket_uuid,
        )

        path = reverse("Xential:interactive-document", args=[bptl_ticket_uuid])
        bptl_interactive_url = get_absolute_url(path)

        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        response = self.client.get(bptl_interactive_url)
        self.assertEqual(status.HTTP_302_FOUND, response.status_code)

        expected_url = "https://xentiallabs.com/xential?resumeApplication=527f6ea1-e292-41ec-ac5b-8f8feddf153f&loginTicketUuid=4c68ae87-1e13-49db-8744-600a4c86a067"
        self.assertEqual(expected_url, response.url)
