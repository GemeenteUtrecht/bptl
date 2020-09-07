from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

import requests_mock
from django_camunda.models import CamundaConfig
from requests.exceptions import ConnectionError

from bptl.tasks.models import TaskMapping
from bptl.utils.constants import Statuses
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory
from bptl.work_units.zgw.tests.utils import mock_service_oas_get

from .factories import ExternalTaskFactory
from .utils import json_variable

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


@requests_mock.Mocker()
class ExecuteCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        config = CamundaConfig.get_solo()
        config.root_url = "https://some.camunda.com"
        config.rest_api_path = "engine-rest/"
        config.save()

        mapping = TaskMapping.objects.create(
            topic_name="zaak-initialize",
            callback="bptl.work_units.zgw.tasks.zaak.CreateZaakTask",
        )
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

    def test_execute_one(self, m):
        task = ExternalTaskFactory.create(
            topic_name="zaak-initialize",
            variables={
                "zaaktype": {"value": ZAAKTYPE},
                "organisatieRSIN": {"value": "123456788"},
                "services": json_variable(
                    {"ZRC": {"jwt": "Bearer 12345"}, "ZTC": {"jwt": "Bearer 789"}}
                ),
            },
        )
        # mock camunda
        m.post(
            f"https://some.camunda.com/engine-rest/external-task/{task.task_id}/complete",
            status_code=204,
        )

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
            json=RESPONSES[ZAAK],
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

        # execute command
        stdout = StringIO()
        call_command("execute_task", task_id=task.id, stdout=stdout)

        task.refresh_from_db()
        self.assertEqual(task.status, Statuses.completed)

        request_body = m.last_request.json()
        self.assertEqual(request_body["workerId"], task.worker_id)
        self.assertEqual(
            request_body["variables"],
            {
                "zaakUrl": {"value": ZAAK, "type": "String"},
                "zaakIdentificatie": {
                    "value": "ZAAK-2020-0000000013",
                    "type": "String",
                },
            },
        )

    @patch("bptl.camunda.tasks.fail_task")
    def test_execute_fail(self, m, mock_fail_task):
        task = ExternalTaskFactory.create(
            topic_name="zaak-initialize",
            variables={
                "zaaktype": {"value": ZAAKTYPE},
                "organisatieRSIN": {"value": "123456788"},
                "services": json_variable(
                    {
                        "ZRC": {"jwt": "Bearer 12345"},
                        "ZTC": {"jwt": "Bearer 789"},
                    }
                ),
            },
        )
        # mock openzaak services
        mock_service_oas_get(m, ZTC_URL, "ztc")
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.post(f"{ZRC_URL}zaken", exc=ConnectionError("some connection error"))

        stdout = StringIO()
        call_command("execute_task", task_id=task.id, stdout=stdout)

        task.refresh_from_db()
        self.assertEqual(task.status, Statuses.failed)
        self.assertTrue(task.execution_error.strip().endswith("some connection error"))

        mock_fail_task.assert_called_once_with(task)
