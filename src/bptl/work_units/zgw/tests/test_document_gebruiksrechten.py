from django.test import TransactionTestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks.documents import SetIndicatieGebruiksrecht

DRC_URL = "https://some.drc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"

DOCUMENT_URL = (
    f"{DRC_URL}enkelvoudiginformatieobjecten/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
)
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"

PATCH_DOCUMENT_RESPONSE = {
    "url": DOCUMENT_URL,
    "indicatieGebruiksrecht": False,
    "lock": "some-lock",
    # rest left out for brevity
}


@requests_mock.Mocker()
class GebruiksrechtDocumentsTests(TransactionTestCase):
    def setUp(self):
        super().setUp()

        mapping = TaskMappingFactory.create(topic_name="some-topic")
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=DRC_URL,
            service__api_type="drc",
            alias="drc",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=ZRC_URL,
            service__api_type="zrc",
            alias="ZRC",
        )

        self.fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaakUrl": serialize_variable(ZAAK),
                "bptlAppId": serialize_variable("some-app-id"),
            },
        )

    def test_patch_indicatie_gebruiksrecht_documents(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            f"{ZRC_URL}zaakinformatieobjecten?zaak={ZAAK}",
            status_code=200,
            json=[
                {"informatieobject": DOCUMENT_URL},
            ],
        )
        mock_service_oas_get(m, DRC_URL, "drc")

        # Mock call to retrieve and lock the document from the API
        m.post(f"{DOCUMENT_URL}/lock", json={"lock": "some-lock"})
        m.patch(DOCUMENT_URL, json=PATCH_DOCUMENT_RESPONSE)
        m.post(f"{DOCUMENT_URL}/unlock", json={}, status_code=204)
        task = SetIndicatieGebruiksrecht(self.fetched_task)
        result = task.perform()

        self.assertEqual(result, {})
        self.assertEqual(m.request_history[-3].method, "POST")
        self.assertEqual(m.request_history[-3].url, f"{DOCUMENT_URL}/lock")
        self.assertEqual(m.request_history[-3].json(), {})
        self.assertEqual(m.request_history[-2].method, "PATCH")
        self.assertEqual(m.request_history[-2].url, DOCUMENT_URL)
        self.assertEqual(
            m.request_history[-2].json(),
            {"indicatieGebruiksrecht": False, "lock": "some-lock"},
        )
        self.assertEqual(m.request_history[-1].method, "POST")
        self.assertEqual(m.request_history[-1].url, f"{DOCUMENT_URL}/unlock")
        self.assertEqual(m.request_history[-1].json(), {"lock": "some-lock"})
