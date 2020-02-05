from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

import requests_mock
from django_camunda.models import CamundaConfig
from requests.exceptions import ConnectionError
from zgw_consumers.models import Service

from camunda_worker.tasks.models import TaskMapping
from camunda_worker.tasks.tests.utils import mock_service_oas_get

from ..constants import Statuses
from ..models import FetchedTask
from .utils import get_fetch_and_lock_response

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAKTYPE = f"{ZTC_URL}zaaktypen/abcd"
STATUSTYPE = f"{ZTC_URL}statustypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
STATUS = f"{ZRC_URL}statussen/b7218c76-7478-41e9-a088-54d2f914a713"


@requests_mock.Mocker()
class ExecuteCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        config = CamundaConfig.get_solo()
        config.root_url = "https://some.camunda.com"
        config.rest_api_path = "engine-rest/"
        config.save()

        Service.objects.create(
            api_root=ZRC_URL, api_type="zrc", label="zrc",
        )
        Service.objects.create(
            api_root=ZTC_URL, api_type="ztc", label="ztc_local",
        )
        TaskMapping.objects.create(
            topic_name="zaak-initialize",
            callback="camunda_worker.tasks.tasks.worker.CreateZaakTask",
        )

    def test_execute_one(self, m):
        # mock camunda
        m.post(
            "https://some.camunda.com/engine-rest/external-task/fetchAndLock",
            json=get_fetch_and_lock_response(
                topic="zaak-initialize",
                variables={
                    "zaaktype": {"type": "String", "value": ZAAKTYPE, "valueInfo": {}},
                    "organisatieRSIN": {
                        "type": "String",
                        "value": "002220647",
                        "valueInfo": {},
                    },
                },
            ),
        )
        m.post(
            "https://some.camunda.com/engine-rest/external-task/anExternalTaskId/complete",
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

        with patch(
            "camunda_worker.external_tasks.camunda.get_worker_id",
            return_value="aWorkerId",
        ) as m_get_worker_id:

            # execute command
            stdout = StringIO()
            call_command("execute_tasks", 1, stdout=stdout)

        task = FetchedTask.objects.get()
        self.assertEqual(task.status, Statuses.completed)

        stdout.seek(0)
        # remove escape characters for pretty print
        lines = (
            line.strip().replace("\x1b[1m", "").replace("\x1b[0m", "")
            for line in stdout.readlines()
        )
        self.assertEqual(next(lines), "Start 'fetch and lock' step")
        self.assertEqual(next(lines), "1 task(s) fetched with worker ID aWorkerId")
        self.assertEqual(next(lines), "")
        self.assertEqual(next(lines), "Start 'execution' step")
        self.assertEqual(next(lines), "1 task(s) succeeded during execution")
        self.assertEqual(next(lines), "0 task(s) failed during execution")
        self.assertEqual(next(lines), "")
        self.assertEqual(next(lines), "Start 'sending process' step")
        self.assertEqual(next(lines), "1 task(s) succeeded during sending process")
        self.assertEqual(next(lines), "0 task(s) failed during sending process")
        self.assertEqual(next(lines), "")

    def test_execute_fail(self, m):
        # mock camunda
        m.post(
            "https://some.camunda.com/engine-rest/external-task/fetchAndLock",
            json=get_fetch_and_lock_response(
                topic="zaak-initialize",
                variables={
                    "zaaktype": {"type": "String", "value": ZAAKTYPE, "valueInfo": {}},
                    "organisatieRSIN": {
                        "type": "String",
                        "value": "002220647",
                        "valueInfo": {},
                    },
                },
            ),
        )

        # mock openzaak services
        mock_service_oas_get(m, ZTC_URL, "ztc")
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.post(f"{ZRC_URL}zaken", exc=ConnectionError("some connection error"))

        with patch(
            "camunda_worker.external_tasks.camunda.get_worker_id",
            return_value="aWorkerId",
        ) as m_get_worker_id:
            # execute command
            stdout = StringIO()
            call_command("execute_tasks", 1, stdout=stdout)

        task = FetchedTask.objects.get()
        self.assertEqual(task.status, Statuses.failed)

        stdout.seek(0)
        # remove escape characters for pretty print
        lines = (
            line.strip().replace("\x1b[1m", "").replace("\x1b[0m", "")
            for line in stdout.readlines()
        )
        self.assertEqual(next(lines), "Start 'fetch and lock' step")
        self.assertEqual(next(lines), "1 task(s) fetched with worker ID aWorkerId")
        self.assertEqual(next(lines), "")
        self.assertEqual(next(lines), "Start 'execution' step")
        self.assertEqual(
            next(lines),
            f"Task {task} has failed during execution: some connection error",
        )
        self.assertEqual(next(lines), "0 task(s) succeeded during execution")
        self.assertEqual(next(lines), "1 task(s) failed during execution")
        self.assertEqual(next(lines), "")
