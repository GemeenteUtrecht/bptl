from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import LookupZaak

ZRC_URL = "https://some.zrc.nl/api/v1/"


@requests_mock.Mocker()
class LookupZaakTests(TestCase):
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
                "identificatie": serialize_variable("ZAAK-001122"),
                "bronorganisatie": serialize_variable("123456782"),
                "services": serialize_variable({"ZRC": {"jwt": "Bearer 12345"}}),
            },
        )

    def test_successful_lookup(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            f"{ZRC_URL}zaken?identificatie=ZAAK-001122&bronorganisatie=123456782",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [
                    {
                        "url": f"{ZRC_URL}zaken/b291502c-2383-4d40-9079-e8aec66eb251",
                        "identificatie": "ZAAK-001122",
                        "bronorganisatie": "123456782",
                        # rest is not relevant
                    }
                ],
            },
        )
        task = LookupZaak(self.fetched_task)

        result = task.perform()

        self.assertEqual(
            result, {"zaakUrl": f"{ZRC_URL}zaken/b291502c-2383-4d40-9079-e8aec66eb251"}
        )

    def test_zaak_not_found(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            f"{ZRC_URL}zaken?identificatie=ZAAK-001122&bronorganisatie=123456782",
            json={
                "count": 0,
                "previous": None,
                "next": None,
                "results": [],
            },
        )
        task = LookupZaak(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"zaakUrl": None})
