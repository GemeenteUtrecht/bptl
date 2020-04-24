from django.test import TestCase

import requests_mock

from bptl.camunda.models import ExternalTask
from bptl.camunda.tests.utils import json_variable
from bptl.tasks.tests.factories import TaskMappingFactory
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory

from ..tasks import RelateerZaak
from .utils import mock_service_oas_get

ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"

BIJDRAGE_ZAAK = f"{ZRC_URL}zaken/20d2a131-be0d-4b0e-b960-0044e46fa4a8"


@requests_mock.Mocker()
class RelateerZaakTests(TestCase):
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
                "zaakUrl": {"type": "String", "value": BIJDRAGE_ZAAK, "valueInfo": {}},
                "hoofdZaakUrl": {"type": "String", "value": ZAAK},
                "bijdrageAard": {"type": "String", "value": "bijdrage"},
                "services": json_variable({"ZRC": {"jwt": "Bearer 12345"}}),
            },
        )

    def test_relate_zaken(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(ZAAK, json={"url": ZAAK, "relevanteAndereZaken": [],})
        m.patch(
            ZAAK,
            status_code=200,
            json={
                "url": ZAAK,
                "relevanteAndereZaken": [
                    {"url": BIJDRAGE_ZAAK, "aardRelatie": "bijdrage",},
                ],
            },
        )

        task = RelateerZaak(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {})
        self.assertEqual(
            m.last_request.json(),
            {
                "relevanteAndereZaken": [
                    {"url": BIJDRAGE_ZAAK, "aardRelatie": "bijdrage",},
                ],
            },
        )
