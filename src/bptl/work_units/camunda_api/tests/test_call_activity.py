import uuid

from django.test import TestCase

import requests_mock
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable

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
            variables={},
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
        started_instance = {
            "links": [
                {
                    "method": "GET",
                    "href": f"{CAMUNDA_API_ROOT}process-instance/subprocess-id",
                    "rel": "self",
                }
            ],
            "id": "subprocess-id",
            "definitionId": f"someProcess:1:{uuid.uuid4()}",
            "businessKey": "",
            "tenantId": None,
            "ended": False,
            "suspended": False,
        }
        m.post(
            f"{CAMUNDA_API_ROOT}process-definition/key/someProcess/start",
            json=started_instance,
        )
        m.post(
            f"{CAMUNDA_API_ROOT}process-definition/someProcess:3:14abd794-40f3-450a-9060-44c6b72c964e/start",
            json=started_instance,
        )

    def test_call_activity_without_mapping(self, m):
        self.fetched_task.variables = {
            "subprocessDefinition": serialize_variable("someProcess"),
        }
        self.fetched_task.save()
        self._mock_camunda(m)
        task = CallActivity(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"processInstanceId": "subprocess-id"})
        self.assertEqual(
            m.last_request.json(),
            {
                "variables": {
                    "zaakUrl": serialize_variable(ZAAK),
                    "telefoon": serialize_variable("06123456789"),
                },
                "businessKey": None,
                "withVariablesInReturn": False,
            },
        )

    def test_call_activity_with_mapping(self, m):
        self.fetched_task.variables = {
            "subprocessDefinition": serialize_variable("someProcess"),
            "variablesMapping": serialize_variable({"zaakUrl": "hoofdZaakUrl"}),
        }
        self.fetched_task.save()

        self._mock_camunda(m)
        task = CallActivity(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"processInstanceId": "subprocess-id"})
        self.assertEqual(
            m.last_request.json(),
            {
                "variables": {"hoofdZaakUrl": serialize_variable(ZAAK)},
                "businessKey": None,
                "withVariablesInReturn": False,
            },
        )

    def test_call_activity_explicit_version(self, m):
        self.fetched_task.variables = {
            "subprocessDefinition": serialize_variable("someProcess"),
            "subprocessDefinitionVersion": serialize_variable(3),
        }

        self.fetched_task.save()
        self._mock_camunda(m)
        process_id = "someProcess:3:14abd794-40f3-450a-9060-44c6b72c964e"
        m.get(
            f"{CAMUNDA_API_ROOT}process-definition?key=someProcess&version=3",
            json=[
                {
                    "id": process_id,
                    "key": "someProcess",
                    "category": "http://bpmn.io/schema/bpmn",
                    "description": None,
                    "name": "Dummy",
                    "version": 3,
                    "resource": "dummy.bpmn",
                    "deploymentId": "277323c7-522b-11ea-b0b2-7ee96954906c",
                    "diagram": None,
                    "suspended": False,
                    "tenantId": None,
                    "versionTag": None,
                    "historyTimeToLive": None,
                    "startableInTasklist": True,
                }
            ],
        )
        task = CallActivity(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"processInstanceId": "subprocess-id"})

        self.assertEqual(
            m.last_request.url,
            f"{CAMUNDA_API_ROOT}process-definition/{process_id}/start",
        )
        self.assertEqual(
            m.last_request.json(),
            {
                "variables": {
                    "zaakUrl": serialize_variable(ZAAK),
                    "telefoon": serialize_variable("06123456789"),
                },
                "businessKey": None,
                "withVariablesInReturn": False,
            },
        )
