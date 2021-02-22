from unittest.mock import patch

from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.camunda.models import ExternalTask
from bptl.tasks.models import TaskMapping
from bptl.tasks.tests.factories import DefaultServiceFactory
from bptl.work_units.xential.models import XentialTicket
from bptl.work_units.xential.tasks import (
    check_failed_document_builds,
    check_xential_document_status,
)

XENTIAL_API_ROOT = "https://xentiallabs.com/xential/modpages/next.oas/api/"


@requests_mock.Mocker()
class DocumentStatusCheckTests(TestCase):
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

        cls.external_task = ExternalTask.objects.create(
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

    def test_check_document_success_status(self, m):
        XentialTicket.objects.create(
            task=self.external_task,
            bptl_ticket_uuid="2d30f19b-8666-4f45-a8da-78ad7ed0ef4d",
            ticket_uuid="f15aceb4-b316-45bc-8353-7906ae125557",
            document_uuid="7911f024-89ce-4600-9a6f-1b4e681efb36",
            is_ticket_complete=False,
        )
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
        m.get(
            f"{XENTIAL_API_ROOT}document/7911f024-89ce-4600-9a6f-1b4e681efb36",
            json={
                "documentUuid": "7911f024-89ce-4600-9a6f-1b4e681efb36",
                "title": "Document title",
                "buildStatus": "SUCCESS",
            },
        )

        check_xential_document_status("2d30f19b-8666-4f45-a8da-78ad7ed0ef4d")

        history = m.request_history

        self.assertEqual(2, len(history))

    def test_check_document_error_status(self, m):
        XentialTicket.objects.create(
            task=self.external_task,
            bptl_ticket_uuid="2d30f19b-8666-4f45-a8da-78ad7ed0ef4d",
            ticket_uuid="f15aceb4-b316-45bc-8353-7906ae125557",
            document_uuid="7911f024-89ce-4600-9a6f-1b4e681efb36",
            is_ticket_complete=False,
        )
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
        m.get(
            f"{XENTIAL_API_ROOT}document/7911f024-89ce-4600-9a6f-1b4e681efb36",
            json={
                "documentUuid": "7911f024-89ce-4600-9a6f-1b4e681efb36",
                "title": "Document title",
                "buildStatus": "ERROR",
            },
        )
        m.post(
            "https://camunda.example.com/engine-rest/external-task/test-task-id/failure"
        )

        check_xential_document_status("2d30f19b-8666-4f45-a8da-78ad7ed0ef4d")

        history = m.request_history

        self.assertEqual(3, len(history))
        self.assertEqual(
            "Xential failed to build the document.", history[-1].json()["errorMessage"]
        )


class PeriodicTaskTests(TestCase):
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

        cls.external_task = ExternalTask.objects.create(
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

    @patch("bptl.work_units.xential.tasks.check_xential_document_status.delay")
    def test_check_document_status_no_document_uuid(
        self, check_xential_document_status
    ):
        XentialTicket.objects.create(
            task=self.external_task,
            bptl_ticket_uuid="2d30f19b-8666-4f45-a8da-78ad7ed0ef4d",
            ticket_uuid="f15aceb4-b316-45bc-8353-7906ae125557",
            is_ticket_complete=False,
        )

        check_failed_document_builds()

        check_xential_document_status.assert_not_called()

    @patch("bptl.work_units.xential.tasks.check_xential_document_status.delay")
    def test_check_multiple_tickets(self, check_xential_document_status):
        XentialTicket.objects.create(
            task=self.external_task,
            bptl_ticket_uuid="2d30f19b-8666-4f45-a8da-78ad7ed0ef4d",
            ticket_uuid="f15aceb4-b316-45bc-8353-7906ae125557",
            document_uuid="7911f024-89ce-4600-9a6f-1b4e681efb36",
            is_ticket_complete=False,
        )
        XentialTicket.objects.create(
            task=self.external_task,
            bptl_ticket_uuid="ce9f214b-db7c-434c-ba8b-1f5169eef109",
            ticket_uuid="3943fb26-59e3-452d-97dc-7205416c8f64",
            document_uuid="353652e6-1ab7-4129-8edc-ebb3ab2a9e0a",
            is_ticket_complete=True,
        )
        XentialTicket.objects.create(
            task=self.external_task,
            bptl_ticket_uuid="ce9f214b-db7c-434c-ba8b-1f5169eef109",
            ticket_uuid="3943fb26-59e3-452d-97dc-7205416c8f64",
            is_ticket_complete=False,
        )

        check_failed_document_builds()

        check_xential_document_status.assert_called_once_with(
            "2d30f19b-8666-4f45-a8da-78ad7ed0ef4d"
        )
