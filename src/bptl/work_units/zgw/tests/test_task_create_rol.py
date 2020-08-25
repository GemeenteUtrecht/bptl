import json

from django.test import TestCase

import requests_mock

from bptl.camunda.models import ExternalTask
from bptl.camunda.tests.utils import json_variable
from bptl.tasks.tests.factories import TaskMappingFactory
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory

from ..tasks import CreateRolTask
from .utils import mock_service_oas_get

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"
ROLTYPE = f"{ZTC_URL}roltypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
ZAAKTYPE = f"{ZTC_URL}zaaktypen/64dae7f9-8d11-4b11-9a10-747acb73630e"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
ROL = f"{ZRC_URL}rollen/b7218c76-7478-41e9-a088-54d2f914a713"


@requests_mock.Mocker()
class CreateRolTaskTests(TestCase):
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
                "zaakUrl": {"type": "String", "value": ZAAK, "valueInfo": {}},
                "omschrijving": {"type": "String", "value": "roltype omschrijving"},
                "betrokkene": json_variable(
                    {
                        "betrokkene": "http://some.api.nl/betrokkenen/12345",
                        "betrokkeneType": "natuurlijk_persoon",
                        "roltoelichting": "A test roltoelichting",
                    }
                ),
                "services": json_variable(
                    {"ZRC": {"jwt": "Bearer 12345"}, "ZTC": {"jwt": "Bearer 789"}}
                ),
            },
        )

    def test_create_rol(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        mock_service_oas_get(m, ZTC_URL, "ztc")
        m.get(ZAAK, json={"url": ZAAK, "zaaktype": ZAAKTYPE})
        m.get(
            f"{ZTC_URL}roltypen?zaaktype={ZAAKTYPE}",
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "url": ROLTYPE,
                        "omschrijving": "roltype omschrijving",
                        "zaaktype": ZAAKTYPE,
                        "omschrijvingGeneriek": "initiator",
                    },
                ],
            },
        )
        m.post(
            f"{ZRC_URL}rollen",
            status_code=201,
            json={
                "url": ROL,
                "zaak": ZAAK,
                "betrokkene": "http://some.api.nl/betrokkenen/12345",
                "betrokkeneType": "natuurlijk_persoon",
                "roltype": ROLTYPE,
                "roltoelichting": "A test roltoelichting",
                "indicatieMachtiging": "",
                "betrokkeneIdentificatie": {},
            },
        )

        task = CreateRolTask(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"rolUrl": ROL})
        self.assertEqual(
            m.last_request.json(),
            {
                "zaak": ZAAK,
                "betrokkene": "http://some.api.nl/betrokkenen/12345",
                "betrokkeneType": "natuurlijk_persoon",
                "roltype": ROLTYPE,
                "roltoelichting": "A test roltoelichting",
                "indicatieMachtiging": "",
                "betrokkeneIdentificatie": {},
            },
        )
