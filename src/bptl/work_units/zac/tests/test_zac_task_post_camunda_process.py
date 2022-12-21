from unittest.mock import patch

from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from requests.exceptions import HTTPError
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.credentials.tests.factories import AppServiceCredentialsFactory
from bptl.tasks.base import MissingVariable
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import StartCamundaProcessTask

ZAC_ROOT = "https://zac.example.com/"
ZRC_ROOT = "https://some.zrc.nl/api/v1/"
ZAAK_URL = f"{ZRC_ROOT}zaken/some-zaak"
ZAC_START_PROCESS_URL = f"{ZAC_ROOT}api/core/cases/123456789/ZAAK-01/start-process"
PROCESS_INSTANCE_ID = "133c2414-1be1-4c24-a520-08f4ebd58d9e"
PROCESS_INSTANCE_URL = (
    f"https://camunda-example.com/engine-rest/process-instance/{PROCESS_INSTANCE_ID}"
)


class ZacStartCamundaProcessTaskTests(TestCase):
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
    def test_post_camunda_start_process_form_from_zaak_url(self, m):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_data = {
            "instanceId": PROCESS_INSTANCE_ID,
            "instanceUrl": PROCESS_INSTANCE_URL,
        }
        m.post(ZAC_START_PROCESS_URL, json=mock_data)
        m.get(
            ZAAK_URL, json={"bronorganisatie": "123456789", "identificatie": "ZAAK-01"}
        )

        task = StartCamundaProcessTask(self.task_url)
        response = task.get_client_response()
        self.assertEqual(response, mock_data)

        cleaned_data = task.perform()
        self.assertEqual(
            m.last_request.url,
            ZAC_START_PROCESS_URL,
        )
        self.assertEqual(cleaned_data, {})

    @requests_mock.Mocker()
    def test_post_camunda_start_process_form_from_zaak_url_missing_return(self, m):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        m.post(ZAC_START_PROCESS_URL, json={})
        m.get(
            ZAAK_URL, json={"bronorganisatie": "123456789", "identificatie": "ZAAK-01"}
        )

        task = StartCamundaProcessTask(self.task_url)
        response = task.get_client_response()
        self.assertEqual(response, {})

        with self.assertRaises(Exception) as e:
            task.perform()

        self.assertEqual(type(e.exception), MissingVariable)
        self.assertEqual(
            e.exception.args[0]["instanceId"][0].__str__(), "Dit veld is vereist."
        )
        self.assertEqual(
            e.exception.args[0]["instanceUrl"][0].__str__(), "Dit veld is vereist."
        )

    @requests_mock.Mocker()
    @patch("bptl.work_units.zac.tasks.logger", return_value=None)
    def test_post_camunda_start_process_form_from_zaak_url_missing_form(
        self, m, mock_logger
    ):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        m.post(
            ZAC_START_PROCESS_URL, json={"Detail": "Niet gevonden."}, status_code=404
        )
        m.get(
            ZAAK_URL, json={"bronorganisatie": "123456789", "identificatie": "ZAAK-01"}
        )

        task = StartCamundaProcessTask(self.task_url)
        with self.assertRaises(HTTPError) as exc:
            response = task.get_client_response()

        self.assertEqual(exc.exception.response.status_code, 404)

    def test_missing_zaak_url_variable(self):
        task_dict = {**self.task_dict}
        task_dict["variables"] = {}
        task_url = ExternalTask.objects.create(
            **task_dict,
        )
        task = StartCamundaProcessTask(task_url)
        with self.assertRaises(Exception) as e:
            task.perform()

        self.assertEqual(type(e.exception), MissingVariable)
        self.assertEqual(
            e.exception.args[0], "The variable zaakUrl is missing or empty."
        )

    def test_empty_zaak_url_variable(self):
        task_dict = {**self.task_dict}
        task_dict["variables"] = {
            "zaakUrl": serialize_variable(""),
        }
        task_url = ExternalTask.objects.create(
            **task_dict,
        )
        task = StartCamundaProcessTask(task_url)
        with self.assertRaises(Exception) as e:
            task.perform()

        self.assertEqual(type(e.exception), MissingVariable)
        self.assertEqual(
            e.exception.args[0], "The variable zaakUrl is missing or empty."
        )
