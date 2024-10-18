from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import RelateerZaak

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
                "zaakUrl": serialize_variable(BIJDRAGE_ZAAK),
                "hoofdZaakUrl": serialize_variable(ZAAK),
                "aardRelatie": serialize_variable("bijdrage"),
                "bptlAppId": serialize_variable("some-app-id"),
            },
        )

    def test_relate_zaken(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            ZAAK,
            json={
                "url": ZAAK,
                "relevanteAndereZaken": [],
            },
        )
        m.get(
            BIJDRAGE_ZAAK,
            json={
                "url": BIJDRAGE_ZAAK,
                "relevanteAndereZaken": [],
            },
        )
        m.patch(
            ZAAK,
            status_code=200,
            json={
                "url": ZAAK,
                "relevanteAndereZaken": [
                    {
                        "url": BIJDRAGE_ZAAK,
                        "aardRelatie": "bijdrage",
                    },
                ],
            },
        )
        m.patch(
            BIJDRAGE_ZAAK,
            status_code=200,
            json={
                "url": BIJDRAGE_ZAAK,
                "relevanteAndereZaken": [
                    {
                        "url": ZAAK,
                        "aardRelatie": "onderwerp",
                    },
                ],
            },
        )

        task = RelateerZaak(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {})
        self.assertEqual(
            m.request_history[-1].json(),
            {
                "relevanteAndereZaken": [
                    {
                        "url": ZAAK,
                        "aardRelatie": "onderwerp",
                    },
                ],
            },
        )
        self.assertEqual(
            m.request_history[-3].json(),
            {
                "relevanteAndereZaken": [
                    {
                        "url": BIJDRAGE_ZAAK,
                        "aardRelatie": "bijdrage",
                    },
                ],
            },
        )

    def test_relateer_zaak_no_hoofdzaak(self, m):
        self.fetched_task.variables["hoofdZaakUrl"] = serialize_variable("")
        self.fetched_task.save()
        task = RelateerZaak(self.fetched_task)

        result = task.perform()

        self.assertIsNone(result)
        self.assertEqual(len(m.request_history), 0)

    def test_relateer_zaak_hoofdzaak_unset(self, m):
        del self.fetched_task.variables["hoofdZaakUrl"]
        self.fetched_task.save()
        task = RelateerZaak(self.fetched_task)

        result = task.perform()

        self.assertIsNone(result)
        self.assertEqual(len(m.request_history), 0)

    def test_relateer_zaak_empty_bijdrage_aard_omgekeerde_richting(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            ZAAK,
            json={
                "url": ZAAK,
                "relevanteAndereZaken": [],
            },
        )
        m.patch(
            ZAAK,
            status_code=200,
            json={
                "url": ZAAK,
                "relevanteAndereZaken": [
                    {
                        "url": BIJDRAGE_ZAAK,
                        "aardRelatie": "bijdrage",
                    },
                ],
            },
        )

        self.fetched_task.variables[
            "aardRelatieOmgekeerdeRichting"
        ] = serialize_variable("")
        self.fetched_task.save()
        task = RelateerZaak(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {})
        self.assertEqual(
            m.last_request.json(),
            {
                "relevanteAndereZaken": [
                    {
                        "url": BIJDRAGE_ZAAK,
                        "aardRelatie": "bijdrage",
                    },
                ],
            },
        )

    def test_relateer_zaak_bijdrage_aard_omgekeerde_richting_invalid(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            ZAAK,
            json={
                "url": ZAAK,
                "relevanteAndereZaken": [],
            },
        )
        m.patch(
            ZAAK,
            status_code=200,
            json={
                "url": ZAAK,
                "relevanteAndereZaken": [
                    {
                        "url": BIJDRAGE_ZAAK,
                        "aardRelatie": "bijdrage",
                    },
                ],
            },
        )

        self.fetched_task.variables[
            "aardRelatieOmgekeerdeRichting"
        ] = serialize_variable("niks")
        self.fetched_task.save()
        task = RelateerZaak(self.fetched_task)

        with self.assertRaises(ValueError) as e:
            task.perform()
        self.assertEqual(
            e.exception.__str__(), "Unknown 'aardRelatieOmgekeerdeRichting': 'niks'"
        )
