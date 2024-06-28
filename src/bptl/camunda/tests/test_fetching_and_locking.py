"""
Test the fetching and locking of external tasks in Camunda.

Example requests and response taken from
https://docs.camunda.org/manual/7.12/reference/rest/external-task/fetch/#example-with-all-variables
"""

from unittest.mock import patch

from django.test import TestCase

import requests_mock
from django_camunda.models import CamundaConfig

from ..models import ExternalTask
from ..utils import fetch_and_lock
from .utils import get_fetch_and_lock_response


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
            json=get_fetch_and_lock_response(
                variables={
                    "orderId": {"type": "String", "value": "1234", "valueInfo": {}}
                }
            ),
        )

        with patch(
            "bptl.camunda.utils.get_worker_id",
            return_value="aWorkerId",
        ) as m_get_worker_id:
            fetch_and_lock(max_tasks=1)

        m_get_worker_id.assert_called_once()

        qs = ExternalTask.objects.all()
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
