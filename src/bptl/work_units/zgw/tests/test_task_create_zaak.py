from django.test import TestCase

import requests_mock

from bptl.camunda.models import ExternalTask
from bptl.camunda.tests.utils import json_variable
from bptl.tasks.tests.factories import TaskMappingFactory
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory

from ..tasks import CreateZaakTask
from .utils import mock_service_oas_get

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAKTYPE = f"{ZTC_URL}zaaktypen/abcd"
STATUSTYPE = f"{ZTC_URL}statustypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
STATUS = f"{ZRC_URL}statussen/b7218c76-7478-41e9-a088-54d2f914a713"

RESPONSES = {
    ZAAK: {
        "url": ZAAK,
        "uuid": "4f8b4811-5d7e-4e9b-8201-b35f5101f891",
        "identificatie": "ZAAK-2020-0000000013",
        "bronorganisatie": "002220647",
        "omschrijving": "",
        "zaaktype": ZAAKTYPE,
        "registratiedatum": "2020-01-16",
        "verantwoordelijkeOrganisatie": "002220647",
        "startdatum": "2020-01-16",
        "einddatum": None,
    },
}


def mock_statustypen_get(m):
    m.get(
        f"{ZTC_URL}statustypen?zaaktype={ZAAKTYPE}",
        json={
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "url": STATUSTYPE,
                    "omschrijving": "initial",
                    "zaaktype": ZAAKTYPE,
                    "volgnummer": 1,
                    "isEindstatus": False,
                    "informeren": False,
                },
            ],
        },
    )


def mock_status_post(m):
    m.post(
        f"{ZRC_URL}statussen",
        status_code=201,
        json={
            "url": STATUS,
            "uuid": "b7218c76-7478-41e9-a088-54d2f914a713",
            "zaak": ZAAK,
            "statustype": STATUSTYPE,
            "datumStatusGezet": "2020-01-16T00:00:00.000000Z",
            "statustoelichting": "",
        },
    )


@requests_mock.Mocker()
class CreateZaakTaskTests(TestCase):
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
        cls.fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaaktype": {"type": "String", "value": ZAAKTYPE, "valueInfo": {}},
                "organisatieRSIN": {
                    "type": "String",
                    "value": "002220647",
                    "valueInfo": {},
                },
                "NLXProcessId": {"type": "String", "value": "12345", "valueInfo": {}},
                "services": json_variable(
                    {"ZRC": {"jwt": "Bearer 12345"}, "ZTC": {"jwt": "Bearer 789"},}
                ),
            },
        )

    def test_create_zaak(self, m):
        mock_service_oas_get(m, ZTC_URL, "ztc")
        mock_service_oas_get(m, ZRC_URL, "zrc")

        mock_statustypen_get(m)
        m.post(f"{ZRC_URL}zaken", status_code=201, json=RESPONSES[ZAAK])
        mock_status_post(m)

        task = CreateZaakTask(self.fetched_task)

        result = task.perform()
        self.assertEqual(
            result,
            {
                "zaak": RESPONSES[ZAAK],
                "zaakUrl": ZAAK,
                "zaakIdentificatie": "ZAAK-2020-0000000013",
            },
        )

        request_zaak = next(
            filter(
                lambda x: x.url == f"{ZRC_URL}zaken" and x.method == "POST",
                m.request_history,
            )
        )
        self.assertEqual(request_zaak.headers["X-NLX-Request-Process-Id"], "12345")
        self.assertEqual(request_zaak.headers["Authorization"], "Bearer 12345")

    def test_extra_variables(self, m):
        self.fetched_task.variables["zaakDetails"] = json_variable(
            {"omschrijving": "foo",}
        )
        self.fetched_task.save(0)

        mock_service_oas_get(m, ZTC_URL, "ztc")
        mock_service_oas_get(m, ZRC_URL, "zrc")

        mock_statustypen_get(m)
        response = RESPONSES[ZAAK].copy()
        response["omschrijving"] = "foo"
        m.post(f"{ZRC_URL}zaken", status_code=201, json=response)
        mock_status_post(m)
        task = CreateZaakTask(self.fetched_task)

        task.perform()

        request_zaak = next(
            filter(
                lambda x: x.url == f"{ZRC_URL}zaken" and x.method == "POST",
                m.request_history,
            )
        )

        self.assertEqual(request_zaak.json()["omschrijving"], "foo")
