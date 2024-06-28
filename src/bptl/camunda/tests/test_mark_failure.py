"""
Test marking tasks as failed to Camunda.

Example requests and response taken from
https://docs.camunda.org/manual/7.12/reference/rest/external-task/post-complete/
"""

from django.test import TestCase

import requests_mock
from django_camunda.models import CamundaConfig

from ..models import ExternalTask
from ..utils import fail_task


@requests_mock.Mocker()
class CompleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        config = CamundaConfig.get_solo()
        config.root_url = "https://some.camunda.com"
        config.rest_api_path = "engine-rest/"
        config.save()

        cls.task = ExternalTask.objects.create(
            worker_id="test-worker-id",
            task_id="test-task-id",
            execution_error="\n".join(["Line 1", "Line 2"]),
        )

    def test_fail_task_with_reason(self, m):
        m.post(
            "https://some.camunda.com/engine-rest/external-task/test-task-id/failure",
            status_code=204,
        )

        fail_task(self.task, "Everything is broken")

        req = m.last_request
        self.assertEqual(
            req.json(),
            {
                "workerId": "test-worker-id",
                "errorMessage": "Everything is broken",
                "errorDetail": "Line 1\nLine 2",
                "retries": 0,
                "retryTimeout": 0,
            },
        )

    def test_fail_without_explicit_reason(self, m):
        m.post(
            "https://some.camunda.com/engine-rest/external-task/test-task-id/failure",
            status_code=204,
        )

        fail_task(self.task)

        req = m.last_request
        self.assertEqual(
            req.json(),
            {
                "workerId": "test-worker-id",
                "errorMessage": "Line 2",
                "errorDetail": "Line 1\nLine 2",
                "retries": 0,
                "retryTimeout": 0,
            },
        )

    def test_fail_without_traceback(self, m):
        self.task.execution_error = ""
        self.task.save()
        m.post(
            "https://some.camunda.com/engine-rest/external-task/test-task-id/failure",
            status_code=204,
        )

        fail_task(self.task)

        req = m.last_request
        self.assertEqual(
            req.json(),
            {
                "workerId": "test-worker-id",
                "errorMessage": "",
                "errorDetail": "",
                "retries": 0,
                "retryTimeout": 0,
            },
        )
