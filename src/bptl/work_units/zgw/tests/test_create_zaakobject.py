import json

from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import CreateZaakObject

ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
OBJECT = "https://some.orc.nl/api/v1/adres/1234"


@requests_mock.Mocker()
class CreateZaakObjectTests(TestCase):
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
                "zaakUrl": serialize_variable(ZAAK),
                "objectUrl": serialize_variable(OBJECT),
                "objectType": serialize_variable("adres"),
                "bptlAppId": serialize_variable("some-id"),
            },
        )

    def test_create_zaakobject(self, m):
        zaakobject_url = f"{ZRC_URL}zaakobjecten/1234"
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.post(
            f"{ZRC_URL}zaakobjecten",
            status_code=201,
            json={
                "url": zaakobject_url,
                "zaak": ZAAK,
                "object": OBJECT,
                "objectType": "adres",
                "objectTypeOverige": "",
                "relatieomschrijving": "",
            },
        )

        task = CreateZaakObject(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"zaakObjectUrl": zaakobject_url})
        self.assertEqual(
            m.last_request.json(),
            {
                "zaak": ZAAK,
                "object": OBJECT,
                "objectType": "adres",
                "objectTypeOverige": "",
                "relatieomschrijving": "",
            },
        )

    def test_create_zaakobject_no_zaak(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")

        fetched_task = self.fetched_task
        fetched_task.variables = {
            **fetched_task.variables,
            **{"zaakUrl": serialize_variable("")},
        }
        fetched_task.save()

        task = CreateZaakObject(fetched_task)
        result = task.perform()
        self.assertEqual(result, {})
        self.assertTrue(all(req.method == "GET" for req in m.request_history))
