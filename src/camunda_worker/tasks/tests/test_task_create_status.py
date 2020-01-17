from django.test import TestCase

import requests_mock
from django_camunda.models import CamundaConfig
from zgw_consumers.models import Service

from camunda_worker.external_tasks.constants import Statuses
from camunda_worker.external_tasks.models import FetchedTask

from ..tasks import CreateStatusTask
from .utils import mock_service_oas_get

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"
STATUSTYPE = f"{ZTC_URL}statustypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
STATUS = f"{ZRC_URL}statussen/b7218c76-7478-41e9-a088-54d2f914a713"


@requests_mock.Mocker(real_http=True)
class CreateZaakTaskTests(TestCase):
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

        cls.fetched_task = FetchedTask.objects.create(
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaak": {"type": "String", "value": ZAAK, "valueInfo": {}},
                "statustype": {"type": "String", "value": STATUSTYPE, "valueInfo": {}},
            },
        )

    def test_create_status(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
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

        task = CreateStatusTask(self.fetched_task)

        task.perform()
        self.fetched_task.refresh_from_db()

        self.assertEqual(self.fetched_task.status, Statuses.completed)
        self.assertEqual(self.fetched_task.result_variables, {"status": STATUS})
