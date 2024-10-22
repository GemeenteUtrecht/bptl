import json

from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import RelatePand

ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"

PAND = "https://bag.basisregistraties.nl/api/v1/panden/1234?geldigOp=2020-04-03"


@requests_mock.Mocker()
class RelatePandTests(TestCase):
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
                "zaakUrl": {"type": "String", "value": ZAAK, "valueInfo": {}},
                "panden": {
                    "type": "Json",
                    "value": json.dumps([PAND]),
                    "valueInfo": {},
                },
                "bptlAppId": serialize_variable("some-app-id"),
            },
        )

    def test_create_resultaat(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.post(
            f"{ZRC_URL}zaakobjecten",
            status_code=201,
            json={
                "url": f"{ZRC_URL}zaakobjecten/1234",
                "zaak": ZAAK,
                "object": "https://bag.basisregistraties.nl/api/v1/panden/1234",
                "objectType": "pand",
                "relatieomschrijving": "",
            },
        )

        task = RelatePand(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {})
        self.assertEqual(
            m.last_request.json(),
            {
                "zaak": ZAAK,
                "object": "https://bag.basisregistraties.nl/api/v1/panden/1234",
                "objectType": "pand",
                "relatieomschrijving": "",
            },
        )
