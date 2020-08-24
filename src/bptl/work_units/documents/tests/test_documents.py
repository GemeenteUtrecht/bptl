from django.test import TestCase

import requests_mock

from bptl.camunda.models import ExternalTask
from bptl.camunda.tests.utils import json_variable
from bptl.tasks.models import TaskMapping
from bptl.work_units.documents.tasks import LockDocumentTask, UnlockDocumentTask
from bptl.work_units.valid_sign.tests.utils import mock_service_oas_get
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory

DRC_URL = "https://some.drc.nl/api/v1/"
DOCUMENT_URL = (
    f"{DRC_URL}enkelvoudiginformatieobjecten/4f8b4811-5d7e-4e9b-8201-b35f5101f891/"
)
LOCK_DOCUMENT_URL = (
    f"{DRC_URL}enkelvoudiginformatieobjecten/4f8b4811-5d7e-4e9b-8201-b35f5101f891/lock"
)
UNLOCK_DOCUMENT_URL = f"{DRC_URL}enkelvoudiginformatieobjecten/4f8b4811-5d7e-4e9b-8201-b35f5101f891/unlock"

GET_DOCUMENT_RESPONSE = {
    "url": DOCUMENT_URL,
    "uuid": "4f8b4811-5d7e-4e9b-8201-b35f5101f891",
    "inhoud": f"{DOCUMENT_URL}content/",
    "titel": "Test Doc 1",
    "bestandsomvang": 14,
}

LOCK_DOCUMENT_RESPONSE = {"lock": "bacbaeaf-600d-4b79-9414-3e1a668addd3"}


@requests_mock.Mocker()
class LockDocumentsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMapping.objects.create(
            topic_name="LockDocument",
            callback="bptl.work_units.documents.tasks.LockDocumentTask",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=DRC_URL,
            service__api_type="drc",
            alias="drc",
        )

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="LockDocument",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "document": {"type": "str", "value": DOCUMENT_URL},
                "services": json_variable({"drc": {"jwt": "Bearer 12345"}}),
            },
        )

    def test_lock_document(self, m):
        mock_service_oas_get(m=m, url=DRC_URL, service="documenten", extension="json")

        # Mock call to retrieve and lock the document from the API
        m.get(DOCUMENT_URL, json=GET_DOCUMENT_RESPONSE)
        m.post(LOCK_DOCUMENT_URL, json=LOCK_DOCUMENT_RESPONSE)

        task = LockDocumentTask(self.fetched_task)

        response = task.perform()

        self.assertIn("lockId", response)
        self.assertEqual(response["lockId"], "bacbaeaf-600d-4b79-9414-3e1a668addd3")


@requests_mock.Mocker()
class UnlockDocumentsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMapping.objects.create(
            topic_name="UnlockDocument",
            callback="bptl.work_units.documents.tasks.UnlockDocumentTask",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=DRC_URL,
            service__api_type="drc",
            alias="drc",
        )

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="UnlockDocument",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "document": {"type": "str", "value": DOCUMENT_URL},
                "lockId": {
                    "type": "str",
                    "value": "bacbaeaf-600d-4b79-9414-3e1a668addd3",
                },
                "services": json_variable({"drc": {"jwt": "Bearer 12345"}}),
            },
        )

    def test_unlock_document(self, m):
        mock_service_oas_get(m=m, url=DRC_URL, service="documenten", extension="json")

        # Mock call to retrieve, lock and unlock the document from the API
        m.get(DOCUMENT_URL, json=GET_DOCUMENT_RESPONSE)
        m.post(UNLOCK_DOCUMENT_URL)  # Unlocking has no response data

        task = UnlockDocumentTask(self.fetched_task)

        response = task.perform()

        self.assertEqual(len(response), 0)
