import json

from django.test import TestCase

import requests_mock
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import RelateDocumentToZaakTask

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

        mapping = TaskMappingFactory.create(topic_name="some-topic")
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=ZRC_URL,
            service__api_type="zrc",
            alias="ZRC",
        )
        cls.fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaak": {"type": "String", "value": ZAAK, "valueInfo": {}},
                "informatieobject": {
                    "type": "String",
                    "value": INFORMATIEOBJECT,
                    "valueInfo": {},
                },
                "services": {
                    "type": "json",
                    "value": json.dumps(
                        {
                            "ZRC": {"jwt": "Bearer 12345"},
                        }
                    ),
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

        result = task.perform()

        self.assertEqual(result, {"zaakinformatieobject": ZAAKINFORMATIEOBJECT})
