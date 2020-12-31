import json

from django.test import TestCase

import requests_mock
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import CloseZaakTask

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAKTYPE = f"{ZTC_URL}zaaktypen/abcd"
STATUSTYPE = f"{ZTC_URL}statustypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
RESULTAATTYPE = f"{ZTC_URL}resultaattypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
STATUS = f"{ZRC_URL}statussen/b7218c76-7478-41e9-a088-54d2f914a713"
RESULTAAT = f"{ZRC_URL}resultaten/b7218c76-7478-41e9-a088-54d2f914a713"


@requests_mock.Mocker()
class CloseZaakTaskTests(TestCase):
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

    @staticmethod
    def _mock_zgw(m):
        mock_service_oas_get(m, ZTC_URL, "ztc")
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            f"{ZTC_URL}statustypen?zaaktype={ZAAKTYPE}",
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "url": STATUSTYPE,
                        "omschrijving": "final",
                        "zaaktype": ZAAKTYPE,
                        "volgnummer": 1,
                        "isEindstatus": True,
                        "informeren": False,
                    },
                ],
            },
        )
        m.get(
            ZAAK,
            json={
                "url": ZAAK,
                "uuid": "4f8b4811-5d7e-4e9b-8201-b35f5101f891",
                "identificatie": "ZAAK-2020-0000000013",
                "bronorganisatie": "002220647",
                "omschrijving": "",
                "zaaktype": ZAAKTYPE,
                "registratiedatum": "2020-01-16",
                "verantwoordelijkeOrganisatie": "002220647",
                "startdatum": "2020-01-16",
                "einddatum": "2020-01-20",
                "archiefnominatie": "blijvend_bewaren",
                "archiefactiedatum": "2025-01-20",
            },
        )
        m.post(
            f"{ZRC_URL}statussen",
            status_code=201,
            json={
                "url": STATUS,
                "uuid": "b7218c76-7478-41e9-a088-54d2f914a713",
                "zaak": ZAAK,
                "statustype": STATUSTYPE,
                "datumStatusGezet": "2020-01-20T00:00:00.000000Z",
                "statustoelichting": "",
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

    def test_close_zaak_without_resultaattype(self, m):
        self._mock_zgw(m)
        fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaak": {"type": "String", "value": ZAAK, "valueInfo": {}},
                "services": {
                    "type": "json",
                    "value": json.dumps(
                        {
                            "ZRC": {"jwt": "Bearer 12345"},
                            "ZTC": {"jwt": "Bearer 789"},
                        }
                    ),
                },
            },
        )

        task = CloseZaakTask(fetched_task)

        result = task.perform()

        self.assertEqual(
            result,
            {
                "einddatum": "2020-01-20",
                "archiefnominatie": "blijvend_bewaren",
                "archiefactiedatum": "2025-01-20",
            },
        )
        history_resultaat = list(
            filter(
                lambda x: x.method == "POST" and x.url == f"{ZRC_URL}resultaten",
                m.request_history,
            )
        )
        self.assertEqual(len(history_resultaat), 0)

    def test_close_zaak_with_resultaattype(self, m):
        self._mock_zgw(m)

        fetched_task = ExternalTask.objects.create(
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
                    "value": json.dumps(
                        {
                            "ZRC": {"jwt": "Bearer 12345"},
                            "ZTC": {"jwt": "Bearer 789"},
                        }
                    ),
                },
            },
        )

        task = CloseZaakTask(fetched_task)

        result = task.perform()

        self.assertEqual(
            result,
            {
                "einddatum": "2020-01-20",
                "archiefnominatie": "blijvend_bewaren",
                "archiefactiedatum": "2025-01-20",
            },
        )
        history_resultaat = list(
            filter(
                lambda x: x.method == "POST" and x.url == f"{ZRC_URL}resultaten",
                m.request_history,
            )
        )
        self.assertEqual(len(history_resultaat), 1)
        self.assertEqual(
            history_resultaat[0].json(),
            {"zaak": ZAAK, "resultaattype": RESULTAATTYPE, "toelichting": ""},
        )
