from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks.documents import SetIndicatieGebruiksrecht

DRC_URL = "https://some.drc.nl/api/v1/"
DOCUMENT_URL = (
    f"{DRC_URL}enkelvoudiginformatieobjecten/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
)

PATCH_DOCUMENT_RESPONSE = {
    "url": DOCUMENT_URL,
    "indicatieGebruiksrecht": False,
    # rest left out for brevity
}


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
                "bptlAppId": serialize_variable("some-app-id"),
            },
        )

    def test_lock_document(self, m):
        mock_service_oas_get(m, DRC_URL, "drc")
        # Mock call to retrieve and lock the document from the API
        m.patch(DOCUMENT_URL, json=PATCH_DOCUMENT_RESPONSE)
        task = SetIndicatieGebruiksrecht(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {})

        self.assertEqual(m.last_request.method, "PATCH")
        self.assertEqual(m.last_request.url, DOCUMENT_URL)
        self.assertEqual(m.last_request.json(), {"indicatieGebruiksrecht": False})
