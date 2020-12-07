from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks.documents import LockDocument, UnlockDocument
from .utils import mock_service_oas_get

DRC_URL = "https://some.drc.nl/api/v1/"
DOCUMENT_URL = (
    f"{DRC_URL}enkelvoudiginformatieobjecten/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
)
LOCK_DOCUMENT_URL = (
    f"{DRC_URL}enkelvoudiginformatieobjecten/4f8b4811-5d7e-4e9b-8201-b35f5101f891/lock"
)
UNLOCK_DOCUMENT_URL = f"{DRC_URL}enkelvoudiginformatieobjecten/4f8b4811-5d7e-4e9b-8201-b35f5101f891/unlock"

LOCK_DOCUMENT_RESPONSE = {"lock": "bacbaeaf-600d-4b79-9414-3e1a668addd3"}


@requests_mock.Mocker()
class LockDocumentsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMappingFactory.create(topic_name="some-topic")
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=DRC_URL,
            service__api_type="drc",
            alias="drc",
        )

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "informatieobject": serialize_variable(DOCUMENT_URL),
                "services": serialize_variable(
                    {
                        "drc": {"jwt": "Bearer 12345"},
                    }
                ),
            },
        )

    def test_lock_document(self, m):
        mock_service_oas_get(m, DRC_URL, "drc")
        # Mock call to retrieve and lock the document from the API
        m.post(LOCK_DOCUMENT_URL, json=LOCK_DOCUMENT_RESPONSE)
        task = LockDocument(self.fetched_task)

        response = task.perform()

        self.assertIn("lockId", response)
        self.assertEqual(response["lockId"], "bacbaeaf-600d-4b79-9414-3e1a668addd3")

        self.assertEqual(m.last_request.method, "POST")
        self.assertEqual(m.last_request.url, LOCK_DOCUMENT_URL)
        self.assertEqual(m.last_request.headers["Authorization"], "Bearer 12345")


@requests_mock.Mocker()
class UnlockDocumentsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMappingFactory.create(topic_name="some-topic")
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=DRC_URL,
            service__api_type="drc",
            alias="drc",
        )

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "informatieobject": serialize_variable(DOCUMENT_URL),
                "lockId": serialize_variable("bacbaeaf-600d-4b79-9414-3e1a668addd3"),
                "services": serialize_variable(
                    {
                        "drc": {"jwt": "Bearer 12345"},
                    }
                ),
            },
        )

    def test_unlock_document(self, m):
        mock_service_oas_get(m, DRC_URL, "drc")
        # Mock call to retrieve, lock and unlock the document from the API
        m.post(UNLOCK_DOCUMENT_URL)  # Unlocking has no response data
        task = UnlockDocument(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {})
        self.assertEqual(m.last_request.method, "POST")
        self.assertEqual(m.last_request.url, UNLOCK_DOCUMENT_URL)
        self.assertEqual(m.last_request.headers["Authorization"], "Bearer 12345")
