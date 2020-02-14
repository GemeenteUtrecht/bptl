from django.conf import settings
from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase

from bptl.tasks.models import TaskMapping
from bptl.utils.constants import Statuses
from bptl.work_units.zgw.tests.utils import mock_service_oas_get

from ..models import ServiceTask
from .utils import TokenAuthMixin

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAKTYPE = f"{ZTC_URL}zaaktypen/abcd"
STATUSTYPE = f"{ZTC_URL}statustypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
STATUS = f"{ZRC_URL}statussen/b7218c76-7478-41e9-a088-54d2f914a713"


class WorkUnitTestCase(TokenAuthMixin, APITestCase):
    @requests_mock.Mocker()
    def test_full_process(self, m):
        TaskMapping.objects.create(
            topic_name="zaak-initialize",
            callback="bptl.work_units.zgw.tasks.CreateZaakTask",
        )

        data = {
            "topic": "zaak-initialize",
            "vars": {
                "zaaktype": ZAAKTYPE,
                "organisatieRSIN": "002220647",
                "ZRC": {"apiRoot": ZRC_URL, "jwt": "Bearer 12345"},
                "ZTC": {"apiRoot": ZTC_URL, "jwt": "Bearer 789"},
            },
        }
        url = reverse("work-unit", args=(settings.REST_FRAMEWORK["DEFAULT_VERSION"],))

        # mock openzaak services
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
                        "omschrijving": "initial",
                        "zaaktype": ZAAKTYPE,
                        "volgnummer": 1,
                        "isEindstatus": False,
                        "informeren": False,
                    },
                ],
            },
        )
        m.post(
            f"{ZRC_URL}zaken",
            status_code=201,
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
                "einddatum": None,
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
                "datumStatusGezet": "2020-01-16T00:00:00.000000Z",
                "statustoelichting": "",
            },
        )

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        service_task = ServiceTask.objects.get()

        self.assertEqual(service_task.topic_name, "zaak-initialize")
        self.assertEqual(service_task.status, Statuses.performed)

        data_response = response.json()
        expected_response = data.copy()
        expected_response["resultVars"] = {"zaak": ZAAK}
        self.assertEqual(data_response, expected_response)
