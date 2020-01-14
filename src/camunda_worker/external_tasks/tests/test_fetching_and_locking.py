"""
Test the fetching and locking of external tasks in Camunda.

Example requests and response taken from
https://docs.camunda.org/manual/7.12/reference/rest/external-task/fetch/#example-with-all-variables
"""
from unittest.mock import patch

from django.test import TestCase

import requests_mock
from django_camunda.models import CamundaConfig

from ..camunda import fetch_and_lock
from ..models import FetchedTask


@requests_mock.Mocker()
class FetchAndLockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        config = CamundaConfig.get_solo()
        config.root_url = "https://some.camunda.com"
        config.rest_api_path = "engine-rest/"
        config.save()

    def test_fetch_one(self, m):
        m.post(
            "https://some.camunda.com/engine-rest/external-task/fetchAndLock",
            json=[
                {
                    "activityId": "anActivityId",
                    "activityInstanceId": "anActivityInstanceId",
                    "errorMessage": "anErrorMessage",
                    "errorDetails": "anErrorDetails",
                    "executionId": "anExecutionId",
                    "id": "anExternalTaskId",
                    "lockExpirationTime": "2015-10-06T16:34:42.00+0200",
                    "processDefinitionId": "aProcessDefinitionId",
                    "processDefinitionKey": "aProcessDefinitionKey",
                    "processInstanceId": "aProcessInstanceId",
                    "tenantId": "tenantOne",
                    "retries": 3,
                    "workerId": "aWorkerId",
                    "priority": 4,
                    "topicName": "createOrder",
                    "businessKey": "aBusinessKey",
                    "variables": {
                        "orderId": {"type": "String", "value": "1234", "valueInfo": {}}
                    },
                }
            ],
        )

        with patch(
            "camunda_worker.external_tasks.camunda.get_worker_id",
            return_value="aWorkerId",
        ) as m_get_worker_id:
            fetch_and_lock(max_tasks=1)

        m_get_worker_id.assert_called_once()

        qs = FetchedTask.objects.all()
        self.assertEqual(qs.count(), 1)
        fetched_task = qs.get()
        self.assertEqual(fetched_task.worker_id, "aWorkerId")
        self.assertEqual(fetched_task.topic_name, "createOrder")
        self.assertEqual(fetched_task.priority, 4)
        self.assertEqual(fetched_task.task_id, "anExternalTaskId")
        self.assertEqual(
            fetched_task.variables,
            {"orderId": {"type": "String", "value": "1234", "valueInfo": {}}},
        )
