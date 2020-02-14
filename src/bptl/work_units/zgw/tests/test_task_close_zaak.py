from django.test import TestCase

import requests_mock
from django_camunda.models import CamundaConfig

from bptl.camunda.models import ExternalTask

from ..tasks import CloseZaakTask
from .utils import mock_service_oas_get

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAKTYPE = f"{ZTC_URL}zaaktypen/abcd"
STATUSTYPE = f"{ZTC_URL}statustypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
STATUS = f"{ZRC_URL}statussen/b7218c76-7478-41e9-a088-54d2f914a713"


@requests_mock.Mocker()
class CloseZaakTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        config = CamundaConfig.get_solo()
        config.root_url = "https://some.camunda.com"
        config.rest_api_path = "engine-rest/"
        config.save()

        cls.fetched_task = ExternalTask.objects.create(
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaak": {"type": "String", "value": ZAAK, "valueInfo": {}},
                "ZRC": {
                    "type": "Object",
                    "value": {"apiRoot": ZRC_URL, "jwt": "Bearer 12345"},
                },
                "ZTC": {
                    "type": "Object",
                    "value": {"apiRoot": ZTC_URL, "jwt": "Bearer 789"},
                },
            },
        )

    def test_close_zaak(self, m):
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

        task = CloseZaakTask(self.fetched_task)

        task.perform()
        self.fetched_task.refresh_from_db()

        self.assertEqual(
            self.fetched_task.result_variables,
            {
                "einddatum": "2020-01-20",
                "archiefnominatie": "blijvend_bewaren",
                "archiefactiedatum": "2025-01-20",
            },
        )
