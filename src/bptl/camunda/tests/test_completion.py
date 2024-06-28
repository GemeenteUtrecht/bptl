"""
Test the fetching and locking of external tasks in Camunda.

Example requests and response taken from
https://docs.camunda.org/manual/7.12/reference/rest/external-task/post-complete/
"""

from unittest.mock import patch

from django.test import TestCase

import requests
import requests_mock
from django_camunda.models import CamundaConfig

from ..models import ExternalTask
from ..utils import complete_task


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
        )

    def test_complete_task_without_variables(self, m):
        m.post(
            "https://some.camunda.com/engine-rest/external-task/test-task-id/complete",
            status_code=204,
        )

        complete_task(self.task)

        self.assertEqual(
            m.last_request.json(),
            {
                "workerId": "test-worker-id",
                "variables": {},
            },
        )

    def test_complete_task_with_variables(self, m):
        m.post(
            "https://some.camunda.com/engine-rest/external-task/test-task-id/complete",
            status_code=204,
        )
        variables = {
            "zaak": "https://example.com/api/v1/zaken/123",
            "foo": 42,
        }

        complete_task(self.task, variables)

        self.assertEqual(
            m.last_request.json(),
            {
                "workerId": "test-worker-id",
                "variables": {
                    "zaak": {
                        "value": "https://example.com/api/v1/zaken/123",
                        "type": "String",
                    },
                    "foo": {"value": 42, "type": "Integer"},
                },
            },
        )

    def test_callback_url_called_on_completion(self, m):
        task = ExternalTask.objects.create(
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "callbackUrl": {
                    "type": "String",
                    "value": "https://callback.example.com/foo",
                }
            },
        )

        m.post(
            "https://some.camunda.com/engine-rest/external-task/test-task-id/complete",
            status_code=204,
        )
        m.post("https://callback.example.com/foo", status_code=204)

        complete_task(task)

        self.assertEqual(len(m.request_history), 2)

        first_request = m.request_history[0]
        self.assertEqual(
            first_request.url,
            "https://some.camunda.com/engine-rest/external-task/test-task-id/complete",
        )

        last_request = m.last_request
        self.assertEqual(last_request.url, "https://callback.example.com/foo")

    def test_retry_behaviour(self, m):
        task = ExternalTask.objects.create(
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={},
        )
        m.post(
            "https://some.camunda.com/engine-rest/external-task/test-task-id/complete",
            status_code=500,
        )

        with patch("bptl.camunda.utils.fail_task"), patch(
            "bptl.utils.decorators.time.sleep"
        ):
            with self.assertRaises(requests.HTTPError):
                complete_task(task)

        self.assertEqual(len(m.request_history), 4)

    def test_retries_failed_task_failed(self, m):
        task = ExternalTask.objects.create(
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={},
        )
        m.post(
            "https://some.camunda.com/engine-rest/external-task/test-task-id/complete",
            status_code=500,
        )
        m.post(
            "https://some.camunda.com/engine-rest/external-task/test-task-id/failure",
            status_code=204,
        )

        with patch("bptl.utils.decorators.time.sleep"):
            with self.assertRaises(requests.HTTPError):
                complete_task(task)

        self.assertEqual(len(m.request_history), 5)

        self.assertEqual(
            m.last_request.url,
            "https://some.camunda.com/engine-rest/external-task/test-task-id/failure",
        )
        self.assertEqual(m.last_request.method, "POST")
        self.assertEqual(
            m.last_request.json(),
            {
                "workerId": "test-worker-id",
                "errorMessage": (
                    "500 Server Error: None for url: https://some.camunda.com/engine-rest/"
                    "external-task/test-task-id/complete"
                ),
                "errorDetail": "",
                "retries": 0,
                "retryTimeout": 0,
            },
        )

    def test_complete_error_in_process_definition(self, m):
        """
        Assert that process execution errors are logged.

        Camunda returns information on HTTP 500 responses. These happen when the service
        task is completed, but the subsequent process execution step has errors unrelated
        to the service task itself. Looking up the traceback on the machine where
        Camunda is running is very debug-unfriendly. so we extract the error and display
        it to the process modeler.
        """
        task = ExternalTask.objects.create(
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={},
        )
        m.post(
            "https://some.camunda.com/engine-rest/external-task/test-task-id/complete",
            status_code=500,
            json={"some": "error"},
            headers={"Content-Type": "application/json"},
        )

        with patch("bptl.utils.decorators.time.sleep"), patch(
            "bptl.camunda.utils.fail_task"
        ):
            with self.assertRaises(requests.HTTPError):
                complete_task(task)

        task.refresh_from_db()
        self.assertEqual(task.camunda_error, {"some": "error"})
