from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import FetchZaakRelaties

ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"

BIJDRAGE_ZAAK = f"{ZRC_URL}zaken/20d2a131-be0d-4b0e-b960-0044e46fa4a8"


@requests_mock.Mocker()
class FetchZaakRelatiesTests(TestCase):
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

    def test_fetch_zaakrelaties(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            ZAAK,
            json={
                "url": ZAAK,
                "relevanteAndereZaken": [
                    {"url": BIJDRAGE_ZAAK, "aardRelatie": "some-aard"}
                ],
            },
        )
        fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "hoofdZaakUrl": serialize_variable(ZAAK),
                "services": serialize_variable({"ZRC": {"jwt": "Bearer 12345"}}),
            },
        )
        task = FetchZaakRelaties(fetched_task)

        result = task.perform()
        self.assertEqual(
            result,
            {"zaakRelaties": [{"url": BIJDRAGE_ZAAK, "aardRelatie": "some-aard"}]},
        )

    def test_fetch_zaakrelaties_no_hoofdzaakurl(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            ZAAK,
            json={
                "url": ZAAK,
                "relevanteAndereZaken": [
                    {"url": BIJDRAGE_ZAAK, "aardRelatie": "some-aard"}
                ],
            },
        )
        fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "services": serialize_variable({"ZRC": {"jwt": "Bearer 12345"}}),
            },
        )
        task = FetchZaakRelaties(fetched_task)

        result = task.perform()
        self.assertEqual(result, None)
