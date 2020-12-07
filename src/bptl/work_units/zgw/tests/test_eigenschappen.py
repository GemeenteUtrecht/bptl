from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import CreateEigenschap
from .utils import mock_service_oas_get

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"

ZAAKTYPE = f"{ZTC_URL}zaaktypen/abcd"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"


def _get_datum_eigenschap(naam: str) -> dict:
    return {
        "url": f"{ZTC_URL}eigenschappen/{naam}",
        "zaaktype": ZAAKTYPE,
        "naam": naam,
        "definitie": "Dummy",
        "toelichting": "",
        "specificatie": {
            "groep": "periode",
            "formaat": "datum",
            "lengte": "8",
            "kardinaliteit": "1",
            "waardenverzameling": [],
        },
    }


@requests_mock.Mocker(real_http=False)
class CreateDocumentRelationTaskTests(TestCase):
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
                "services": serialize_variable(
                    {
                        "ZRC": {"jwt": "Bearer 12345"},
                        "ZTC": {"jwt": "Bearer 12345"},
                    }
                ),
                "zaakUrl": serialize_variable(ZAAK),
                "eigenschap": serialize_variable(
                    {
                        "naam": "start",
                        "waarde": "2020-05-01",
                    }
                ),
            },
        )

    def test_relate_eigenschap(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        mock_service_oas_get(m, ZTC_URL, "ztc")

        m.get(ZAAK, json={"zaaktype": ZAAKTYPE})
        # https://catalogi-api.vng.cloud/api/v1/schema/#operation/eigenschap_list
        m.get(
            f"{ZTC_URL}eigenschappen?zaaktype={ZAAKTYPE}",
            json={
                "count": 2,
                "next": f"{ZTC_URL}eigenschappen?zaaktype={ZAAKTYPE}&page=2",
                "previous": None,
                "results": [_get_datum_eigenschap("start")],
            },
        )
        m.get(
            f"{ZTC_URL}eigenschappen?zaaktype={ZAAKTYPE}&page=2",
            json={
                "count": 2,
                "next": None,
                "previous": f"{ZTC_URL}eigenschappen?zaaktype={ZAAKTYPE}&page=1",
                "results": [_get_datum_eigenschap("einde")],
            },
        )
        m.post(
            f"{ZAAK}/zaakeigenschappen",
            status_code=201,
            json={
                "url": f"{ZAAK}/eigenschappen/1234",
                "uuid": "1234",
                "zaak": ZAAK,
                "eigenschap": f"{ZTC_URL}eigenschappen/start",
                "naam": "start",
                "waarde": "2020-05-01",
            },
        )

        task = CreateEigenschap(self.fetched_task)
        task.perform()

        self.assertEqual(
            m.last_request.json(),
            {
                "zaak": ZAAK,
                "eigenschap": f"{ZTC_URL}eigenschappen/start",
                "waarde": "2020-05-01",
            },
        )

    def test_eigenschap_does_not_exist(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        mock_service_oas_get(m, ZTC_URL, "ztc")

        m.get(ZAAK, json={"zaaktype": ZAAKTYPE})
        # https://catalogi-api.vng.cloud/api/v1/schema/#operation/eigenschap_list
        m.get(
            f"{ZTC_URL}eigenschappen?zaaktype={ZAAKTYPE}",
            json={
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            },
        )

        task = CreateEigenschap(self.fetched_task)
        task.perform()

        self.assertTrue(all(req.method == "GET" for req in m.request_history))
