from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.credentials.tests.factories import AppServiceCredentialsFactory
from bptl.tasks.base import MissingVariable
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import ZaakDetailURLTask

ZAC_ROOT = "https://zac.example.com/"
ZRC_ROOT = "https://some.zrc.nl/api/v1/"
ZAAK_URL = f"{ZRC_ROOT}zaken/some-zaak"
ZAC_DETAIL_URL = f"{ZAC_ROOT}api/cases/123456789/ZAAK-01/url"


class ZacTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "zaakUrl": serialize_variable(ZAAK_URL),
                "bptlAppId": serialize_variable("some-app-id"),
            },
        }
        cls.task_url = ExternalTask.objects.create(
            **cls.task_dict,
        )

        mapping = TaskMappingFactory.create(topic_name="some-topic-name")
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=ZAC_ROOT,
            service__api_type=APITypes.orc,
            service__auth_type=AuthTypes.no_auth,
            alias="zac",
        )
        cls.zrc_service = Service.objects.create(
            label="zrc",
            api_type=APITypes.zrc,
            api_root=ZRC_ROOT,
            auth_type=AuthTypes.no_auth,
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service=cls.zrc_service,
            alias="zrc",
        )
        AppServiceCredentialsFactory.create(
            app__app_id="some-app-id",
            service=cls.zrc_service,
        )

    @requests_mock.Mocker()
    def test_get_zaak_detail_url_from_zaak_url(self, m):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_data = {
            "zaakDetailUrl": f"{ZAC_ROOT}ui/zaken/some-zaak",
        }
        m.get(ZAC_DETAIL_URL, json=mock_data)
        m.get(
            ZAAK_URL, json={"bronorganisatie": "123456789", "identificatie": "ZAAK-01"}
        )

        task = ZaakDetailURLTask(self.task_url)
        response = task.get_client_response()
        expected_response = {
            "zaakDetailUrl": f"{ZAC_ROOT}ui/zaken/some-zaak",
        }
        self.assertEqual(response, expected_response)

        cleaned_data = task.perform()
        self.assertEqual(
            m.last_request.url,
            ZAC_DETAIL_URL,
        )
        self.assertEqual(cleaned_data, expected_response)

    def test_get_zaak_detail_url_from_zaak_url_missing_zaak_url_variable(self):
        task_dict = {**self.task_dict}
        task_dict["variables"] = {}
        task_url = ExternalTask.objects.create(
            **task_dict,
        )
        task = ZaakDetailURLTask(task_url)
        with self.assertRaises(Exception) as e:
            task.perform()

        self.assertEqual(type(e.exception), MissingVariable)
        self.assertEqual(
            e.exception.args[0], "The variable zaakUrl is missing or empty."
        )

    def test_get_zaak_detail_url_empty_zaak_url_variable(self):
        task_dict = {**self.task_dict}
        task_dict["variables"] = {
            "zaakUrl": serialize_variable(""),
        }
        task_url = ExternalTask.objects.create(
            **task_dict,
        )
        task = ZaakDetailURLTask(task_url)
        with self.assertRaises(Exception) as e:
            task.perform()

        self.assertEqual(type(e.exception), MissingVariable)
        self.assertEqual(
            e.exception.args[0], "The variable zaakUrl is missing or empty."
        )
