import json

from django.test import TestCase

import requests_mock

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import TaskMappingFactory
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory

from ..tasks import CreateResultaatTask
from .utils import mock_service_oas_get

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"
RESULTAATTYPE = f"{ZTC_URL}resultaattypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
RESULTAAT = f"{ZRC_URL}resultaten/b7218c76-7478-41e9-a088-54d2f914a713"


@requests_mock.Mocker(real_http=True)
class CreateResultaatTaskTests(TestCase):
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
                "resultaattype": {
                    "type": "String",
                    "value": RESULTAATTYPE,
                    "valueInfo": {},
                },
                "services": {
                    "type": "json",
                    "value": json.dumps({"ZRC": {"jwt": "Bearer 12345"},}),
                },
            },
        )

    def test_create_resultaat(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.post(
            f"{ZRC_URL}resultaten",
            status_code=201,
            json={
                "url": RESULTAAT,
                "uuid": "7b1f6054-1e65-437e-a2b7-feadf9c27941",
                "zaak": ZAAK,
                "resultaattype": RESULTAATTYPE,
                "toelichting": "some resultaat",
            },
        )

        task = CreateResultaatTask(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"resultaatUrl": RESULTAAT})
