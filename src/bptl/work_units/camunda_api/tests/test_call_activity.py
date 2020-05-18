from django.test import TestCase

import requests_mock
from django_camunda.models import CamundaConfig

from bptl.camunda.models import ExternalTask

from ..tasks import CallActivity

CAMUNDA_ROOT = "https://camunda.example.com/"
CAMUNDA_API_ROOT = f"{CAMUNDA_ROOT}engine-rest/"
ZAAK = "http://some.zrc.nl/api/v1/zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"


@requests_mock.Mocker()
class CallActivityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        camunda = CamundaConfig.get_solo()
        camunda.root_url = CAMUNDA_ROOT
        camunda.save()

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "subprocessDefinitionId": {
                    "type": "String",
                    "value": "subprocess-definition-id",
                    "valueInfo": {},
                },
            },
        )

    def _mock_camunda(self, m):
        m.get(
            f"{CAMUNDA_API_ROOT}external-task/{self.fetched_task.task_id}",
            json={
                "id": self.fetched_task.task_id,
                "processInstanceId": "test-instance-id",
            },
        )
        m.get(
            f"{CAMUNDA_API_ROOT}process-instance/test-instance-id/variables",
            json={
                "zaakUrl": {"type": "String", "value": ZAAK, "valueInfo": {}},
                "telefoon": {"type": "String", "value": "06123456789", "valueInfo": {}},
            },
        )
        m.post(
            f"{CAMUNDA_API_ROOT}process-definition/subprocess-definition-id/start",
            json={
                "links": [
                    {
                        "method": "GET",
                        "href": f"{CAMUNDA_API_ROOT}process-instance/subprocess-id",
                        "rel": "self",
                    }
                ],
                "id": "subprocess-id",
                "definitionId": "subprocess-definition-id",
                "businessKey": "myBusinessKey",
                "tenantId": None,
                "ended": False,
                "suspended": False,
            },
        )

    def test_call_activity_without_mapping(self, m):
        self._mock_camunda(m)
        task = CallActivity(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"processInstanceId": "subprocess-id"})
        self.assertEqual(
            m.last_request.json(),
            {
                "variables": {
                    "zaakUrl": {"type": "String", "value": ZAAK},
                    "telefoon": {"type": "String", "value": "06123456789"},
                },
                "businessKey": None,
                "withVariablesInReturn": False,
            },
        )

    def test_call_activity_with_mapping(self, m):
        self.fetched_task.variables = {
            "subprocessDefinitionId": {
                "type": "String",
                "value": "subprocess-definition-id",
                "valueInfo": {},
            },
            "variablesMapping": {
                "type": "Json",
                "value": '{"zaakUrl": "hoofdZaakUrl"}',
                "valueInfo": {},
            },
        }
        self.fetched_task.save()

        self._mock_camunda(m)
        task = CallActivity(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"processInstanceId": "subprocess-id"})
        self.assertEqual(
            m.last_request.json(),
            {
                "variables": {"hoofdZaakUrl": {"type": "String", "value": ZAAK},},
                "businessKey": None,
                "withVariablesInReturn": False,
            },
        )
