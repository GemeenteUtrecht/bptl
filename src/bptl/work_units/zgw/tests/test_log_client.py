from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.tests.factories import ExternalTaskFactory
from bptl.credentials.api import get_credentials
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks.base import ZGWWorkUnit

ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"


@requests_mock.Mocker()
class ZGWClientLogTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.mapping = TaskMappingFactory.create(topic_name="some-topic")
        zrc_svc = DefaultServiceFactory.create(
            task_mapping=cls.mapping,
            service__api_type=APITypes.zrc,
            service__api_root=ZRC_URL,
            alias="ZRC",
        )
        cls.zrc = zrc_svc.service
        cls.task = ExternalTaskFactory.create(
            topic_name="some-topic",
            variables={
                "bptlAppId": serialize_variable("some-id"),
            },
        )
        cls.work_unit = ZGWWorkUnit(cls.task)

    def test_log_client_retrieve(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        mock_zaak_data = {"url": ZAAK, "identificatie": "ZAAK-2020-0000000013"}
        m.get(ZAAK, json=mock_zaak_data)
        client = self.work_unit.get_client(APITypes.zrc)

        client.retrieve("zaak", ZAAK)

        self.assertEqual(self.task.logs.count(), 1)

        log = self.task.logs.get()

        app_id = self.task.get_variables().get("bptlAppId")
        auth_header = get_credentials(app_id, self.zrc)[self.zrc]
        self.assertEqual(
            log.extra_data,
            {
                "service_base_url": "https://some.zrc.nl",
                "request": {
                    "url": ZAAK,
                    "data": None,
                    "method": "GET",
                    "params": None,
                    "headers": {
                        "Accept": "application/json",
                        "Accept-Crs": "EPSG:4326",
                        "Content-Crs": "EPSG:4326",
                        "Content-Type": "application/json",
                        "Authorization": auth_header["Authorization"],
                    },
                },
                "response": {
                    "data": mock_zaak_data,
                    "status": 200,
                    "headers": {},
                },
            },
        )

    def test_log_client_create(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        mock_zaak_data = {"url": ZAAK, "identificatie": "ZAAK-2020-0000000013"}
        m.post(f"{ZRC_URL}zaken", json=mock_zaak_data, status_code=201)
        client = self.work_unit.get_client(APITypes.zrc)
        post_data = {"someVar": "some value"}

        client.create("zaak", post_data)

        self.assertEqual(self.task.logs.count(), 1)

        log = self.task.logs.get()

        app_id = self.task.get_variables().get("bptlAppId")
        auth_header = get_credentials(app_id, self.zrc)[self.zrc]
        self.assertEqual(
            log.extra_data,
            {
                "service_base_url": "https://some.zrc.nl",
                "request": {
                    "url": f"{ZRC_URL}zaken",
                    "data": post_data,
                    "method": "POST",
                    "params": None,
                    "headers": {
                        "Accept": "application/json",
                        "Accept-Crs": "EPSG:4326",
                        "Content-Crs": "EPSG:4326",
                        "Content-Type": "application/json",
                        "Authorization": auth_header["Authorization"],
                    },
                },
                "response": {
                    "data": mock_zaak_data,
                    "status": 201,
                    "headers": {},
                },
            },
        )
