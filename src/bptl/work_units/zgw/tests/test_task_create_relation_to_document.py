from django.test import TestCase

import requests_mock
from django_camunda.models import CamundaConfig

from bptl.camunda.models import ExternalTask

from ..tasks import RelateDocumentToZaakTask
from .utils import mock_service_oas_get

ZRC_URL = "https://some.zrc.nl/api/v1/"
DRC_URL = "https://some.drc.nl/api/v1/"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
INFORMATIEOBJECT = (
    f"{DRC_URL}enkelvoudiginformatieobjecten/b7218c76-7478-41e9-a088-54d2f914a713"
)
ZAAKINFORMATIEOBJECT = (
    f"{ZRC_URL}zaakinformatieobjecten/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
)


@requests_mock.Mocker(real_http=True)
class CreateDocumentRelationTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        config = CamundaConfig.get_solo()
        config.root_url = "https://some.camunda.com"
        config.rest_api_path = "engine-rest/"
        config.save()

        cls.fetched_task = ExternalTask.objects.create(
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaak": {"type": "String", "value": ZAAK, "valueInfo": {}},
                "informatieobject": {
                    "type": "String",
                    "value": INFORMATIEOBJECT,
                    "valueInfo": {},
                },
                "ZRC": {
                    "type": "Object",
                    "value": {"apiRoot": ZRC_URL, "jwt": "Bearer 12345"},
                },
            },
        )

    def test_create_relation_to_document(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.post(
            f"{ZRC_URL}zaakinformatieobjecten",
            status_code=201,
            json={
                "url": ZAAKINFORMATIEOBJECT,
                "uuid": "b7218c76-7478-41e9-a088-54d2f914a713",
                "zaak": ZAAK,
                "informatieobject": INFORMATIEOBJECT,
                "aardRelatieWeergave": "Hoort bij, omgekeerd: kent",
                "titel": "",
                "beschrijving": "",
                "registratiedatum": "2020-01-16T00:00:00.000000Z",
            },
        )

        task = RelateDocumentToZaakTask(self.fetched_task)

        task.perform()
        self.fetched_task.refresh_from_db()

        self.assertEqual(
            self.fetched_task.result_variables,
            {"zaakinformatieobject": ZAAKINFORMATIEOBJECT},
        )
