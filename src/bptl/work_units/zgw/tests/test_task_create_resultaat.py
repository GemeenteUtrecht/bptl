import json

from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable

from bptl.camunda.models import ExternalTask
from bptl.tasks.base import MissingVariable
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory
from bptl.work_units.zgw.tests.compat import (
    generate_oas_component,
    mock_service_oas_get,
)

from ..tasks import CreateResultaatTask

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"
RESULTAATTYPE = f"{ZTC_URL}resultaattypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
ZAAKTYPE = f"{ZTC_URL}zaaktypen/fb48d7c8-a670-4fa6-a9f5-9d6279b46c9a"
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
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=ZTC_URL,
            service__api_type="ztc",
            alias="ZTC",
        )

    def setUp(self):
        self.fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaak": serialize_variable(ZAAK),
                "resultaattype": serialize_variable(RESULTAATTYPE),
                "bptlAppId": serialize_variable("some-app-id"),
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

    def test_create_resultaat_missing_variables(self, m):
        self.fetched_task.variables["resultaattype"] = serialize_variable("")
        self.fetched_task.save()
        task = CreateResultaatTask(self.fetched_task)

        with self.assertRaises(MissingVariable) as e:
            task.perform()
        self.assertEqual(
            e.exception.__str__(),
            "Missing both resultaattype and omschrijving. One is required.",
        )

    def test_create_resultaat_no_resultaattype_found(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        mock_service_oas_get(m, ZTC_URL, "ztc")
        self.fetched_task.variables["resultaattype"] = serialize_variable("")
        self.fetched_task.variables["omschrijving"] = serialize_variable(
            "some-omschrijving"
        )
        self.fetched_task.save()
        task = CreateResultaatTask(self.fetched_task)
        zaak = generate_oas_component("zrc", "schemas/Zaak", zaaktype=ZAAKTYPE)
        m.get(ZAAK, json=zaak)
        m.get(
            f"{ZTC_URL}resultaattypen?zaaktype={ZAAKTYPE}",
            json={"count": 0, "next": None, "previous": None, "results": []},
        )
        with self.assertRaises(ValueError) as e:
            task.perform()
        self.assertEqual(
            e.exception.__str__(),
            "No resultaattypen were found for zaaktype %s." % ZAAKTYPE,
        )

    def test_create_resultaat_no_resultaattype_found_with_omschrijving(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        mock_service_oas_get(m, ZTC_URL, "ztc")
        self.fetched_task.variables["resultaattype"] = serialize_variable("")
        self.fetched_task.variables["omschrijving"] = serialize_variable(
            "some-omschrijving"
        )
        self.fetched_task.save()
        task = CreateResultaatTask(self.fetched_task)
        zaak = generate_oas_component("zrc", "schemas/Zaak", zaaktype=ZAAKTYPE)
        resultaattype = generate_oas_component(
            "ztc",
            "schemas/ResultaatType",
            omschrijving="some-other-omschrijving",
            url=ZAAKTYPE,
        )
        m.get(ZAAK, json=zaak)
        m.get(
            f"{ZTC_URL}resultaattypen?zaaktype={ZAAKTYPE}",
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [resultaattype],
            },
        )
        with self.assertRaises(ValueError) as e:
            task.perform()
        self.assertEqual(
            e.exception.__str__(),
            "No resultaattype was found with zaaktype %s and omschrijving %s."
            % (ZAAKTYPE, "some-omschrijving"),
        )

    def test_create_resultaat_no_unique_resultaattype_found_with_omschrijving(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        mock_service_oas_get(m, ZTC_URL, "ztc")
        self.fetched_task.variables["resultaattype"] = serialize_variable("")
        self.fetched_task.variables["omschrijving"] = serialize_variable(
            "some-omschrijving"
        )
        self.fetched_task.save()
        task = CreateResultaatTask(self.fetched_task)
        zaak = generate_oas_component("zrc", "schemas/Zaak", zaaktype=ZAAKTYPE)
        resultaattype = generate_oas_component(
            "ztc",
            "schemas/ResultaatType",
            omschrijving="some-omschrijving",
            url=ZAAKTYPE,
        )
        m.get(ZAAK, json=zaak)
        m.get(
            f"{ZTC_URL}resultaattypen?zaaktype={ZAAKTYPE}",
            json={
                "count": 2,
                "next": None,
                "previous": None,
                "results": [resultaattype, resultaattype],
            },
        )
        with self.assertRaises(ValueError) as e:
            task.perform()
        self.assertEqual(
            e.exception.__str__(),
            "No unique resultaattype was found with zaaktype %s and omschrijving %s."
            % (ZAAKTYPE, "some-omschrijving"),
        )

    def test_create_resultaat_with_omschrijving(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        mock_service_oas_get(m, ZTC_URL, "ztc")
        self.fetched_task.variables["resultaattype"] = serialize_variable("")
        self.fetched_task.variables["omschrijving"] = serialize_variable(
            "some-omschrijving"
        )
        self.fetched_task.save()
        task = CreateResultaatTask(self.fetched_task)
        zaak = generate_oas_component("zrc", "schemas/Zaak", zaaktype=ZAAKTYPE)
        resultaattype = generate_oas_component(
            "ztc",
            "schemas/ResultaatType",
            omschrijving="some-omschrijving",
            url=ZAAKTYPE,
        )
        m.get(ZAAK, json=zaak)
        m.get(
            f"{ZTC_URL}resultaattypen?zaaktype={ZAAKTYPE}",
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [resultaattype],
            },
        )
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
        result = task.perform()

        self.assertEqual(result, {"resultaatUrl": RESULTAAT})
