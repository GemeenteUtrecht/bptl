from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.api_models.constants import RolTypes
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.constants import AssigneeTypeChoices
from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import CreateRolTask

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAC_URL = "https://zac.example.com/"
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
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=ZAC_URL,
            service__api_type=APITypes.orc,
            service__auth_type=AuthTypes.no_auth,
            alias="zac",
        )
        cls.fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaakUrl": serialize_variable(ZAAK),
                "omschrijving": serialize_variable("roltype omschrijving"),
                "betrokkene": serialize_variable(
                    {
                        "betrokkene": "http://some.api.nl/betrokkenen/12345",
                        "betrokkeneType": RolTypes.natuurlijk_persoon,
                        "roltoelichting": "A test roltoelichting",
                    }
                ),
                "services": serialize_variable(
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
                "betrokkeneType": RolTypes.natuurlijk_persoon,
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
                "betrokkeneType": RolTypes.natuurlijk_persoon,
                "roltype": ROLTYPE,
                "roltoelichting": "A test roltoelichting",
                "indicatieMachtiging": "",
                "betrokkeneIdentificatie": {},
            },
        )

    def test_create_rol_user_known_in_zac(self, m):
        mock_service_oas_get(m, ZAC_URL, "zac")
        user = f"{AssigneeTypeChoices.user}:some-user"
        zac_betrokkene_identificatie_url = (
            f"{ZAC_URL}api/core/rollen/medewerker/betrokkeneIdentificatie"
        )
        m.post(
            zac_betrokkene_identificatie_url,
            json={
                "betrokkeneIdentificatie": {
                    "voorletters": "S.",
                    "achternaam": "User",
                    "identificatie": user,
                    "voorvoegselAchternaam": "",
                }
            },
        )

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
                "betrokkeneType": RolTypes.medewerker,
                "roltype": ROLTYPE,
                "roltoelichting": "A test roltoelichting",
                "indicatieMachtiging": "",
                "betrokkeneIdentificatie": {
                    "voorletters": "S.",
                    "achternaam": "User",
                    "identificatie": user,
                    "voorvoegselAchternaam": "",
                },
            },
        )

        fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaakUrl": serialize_variable(ZAAK),
                "omschrijving": serialize_variable("roltype omschrijving"),
                "betrokkene": serialize_variable(
                    {
                        "betrokkeneType": RolTypes.medewerker,
                        "roltoelichting": "A test roltoelichting",
                        "betrokkeneIdentificatie": {
                            "identificatie": f"{AssigneeTypeChoices.user}:some-user"
                        },
                    }
                ),
                "services": serialize_variable(
                    {"ZRC": {"jwt": "Bearer 12345"}, "ZTC": {"jwt": "Bearer 789"}}
                ),
            },
        )
        task = CreateRolTask(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"rolUrl": ROL})
        self.assertEqual(
            m.last_request.json(),
            {
                "zaak": ZAAK,
                "betrokkene": "",
                "betrokkeneType": RolTypes.medewerker,
                "roltype": ROLTYPE,
                "roltoelichting": "A test roltoelichting",
                "indicatieMachtiging": "",
                "betrokkeneIdentificatie": {
                    "voorletters": "S.",
                    "achternaam": "User",
                    "identificatie": "user:some-user",
                    "voorvoegselAchternaam": "",
                },
            },
        )

    def test_no_create_rol_empty_omschrijving(self, m):
        self.fetched_task.variables["omschrijving"] = serialize_variable("")
        task = CreateRolTask(self.fetched_task)

        result = task.perform()

        self.assertIsNone(result)
        self.assertEqual(len(m.request_history), 0)

    def test_no_create_rol_group(self, m):
        fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaakUrl": serialize_variable(ZAAK),
                "omschrijving": serialize_variable("roltype omschrijving"),
                "betrokkene": serialize_variable(
                    {
                        "betrokkeneType": RolTypes.medewerker,
                        "roltoelichting": "A test roltoelichting",
                        "betrokkeneIdentificatie": {
                            "identificatie": f"{AssigneeTypeChoices.group}:some-group"
                        },
                    }
                ),
                "services": serialize_variable(
                    {"ZRC": {"jwt": "Bearer 12345"}, "ZTC": {"jwt": "Bearer 789"}}
                ),
            },
        )
        task = CreateRolTask(fetched_task)

        result = task.perform()

        self.assertIsNone(result)
        self.assertEqual(len(m.request_history), 0)
