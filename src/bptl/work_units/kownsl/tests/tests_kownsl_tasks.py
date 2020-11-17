import copy
import datetime
import uuid

from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.camunda.models import ExternalTask
from bptl.tasks.models import TaskMapping
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory

from ..tasks import (
    get_approval_toelichtingen,
    get_client,
    get_email_details,
    get_review_request,
    get_review_request_reminder_date,
    get_review_response_status,
    set_review_request_metadata,
)
from .utils import mock_service_oas_get

KOWNSL_API_ROOT = "https://kownsl.nl/"


@requests_mock.Mocker()
class KownslAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMapping.objects.create(
            topic_name="some-topic",
        )

        cls.service = Service.objects.create(
            label="Kownsl",
            api_type=APITypes.orc,
            api_root=KOWNSL_API_ROOT,
            auth_type=AuthTypes.api_key,
            header_key="Authorization",
            header_value="Token foobarbaz",
            oas=f"{KOWNSL_API_ROOT}schema/openapi.yaml",
        )

        DefaultServiceFactory.create(
            task_mapping=mapping,
            service=cls.service,
            alias="kownsl",
        )

        cls.task_dict = {
            "topic_name": "some-topic",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "kownslReviewRequestId": serialize_variable("1"),
            },
        }

    def test_client(self, m):
        mock_service_oas_get(m, KOWNSL_API_ROOT, "kownsl")
        task = ExternalTask.objects.create(
            **self.task_dict,
        )
        client = get_client(task)
        self.assertIsInstance(client.schema, dict)
        self.assertIsNone(client.auth)
        self.assertEqual(client.auth_header, {"Authorization": "Token foobarbaz"})
        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(m.last_request.url, f"{self.service.oas}?v=3")

    def test_get_review_request(self, m):
        task = ExternalTask.objects.create(
            **self.task_dict,
        )

        response = {
            "id": "1",
            "for_zaak": "https://zaken.nl/api/v1/zaak/123",
            "review_type": "advice",
        }
        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests/1",
            json=response,
        )

        review_requests = get_review_request(task)
        self.assertEqual(review_requests["id"], "1")

    def test_get_review_response_status(self, m):
        rr_response = {
            "id": "1",
            "for_zaak": "https://zaken.nl/api/v1/zaak/123",
            "review_type": "advice",
        }
        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests/1",
            json=rr_response,
        )

        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["kownslUsers"] = serialize_variable(
            ["Zeus", "Poseidon", "Hades"]
        )

        task = ExternalTask.objects.create(
            **task_dict,
        )

        advice_response = [
            {
                "author": "Zeus",
            },
            {
                "author": "Poseidon",
            },
        ]

        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests/1/advices", json=advice_response
        )

        remindThese = get_review_response_status(task)
        self.assertTrue(remindThese["remindThese"][0], "Hades")

    def test_get_review_request_reminder_date(self, m):
        rr_response = {
            "id": "1",
            "for_zaak": "https://zaken.nl/api/v1/zaak/123",
            "review_type": "advice",
            "user_deadlines": {
                "Zeus": "2020-04-20",
                "Poseidon": "2020-04-20",
                "Hades": "2020-04-20",
                "Hera": "2021-04-20",
                "Demeter": "2021-04-20",
            },
        }
        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests/1",
            json=rr_response,
        )

        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["kownslUsers"] = serialize_variable(
            ["Zeus", "Poseidon", "Hades"]
        )

        task = ExternalTask.objects.create(
            **task_dict,
        )

        reminderDate = get_review_request_reminder_date(task)
        self.assertEqual(reminderDate["reminderDate"], "2020-04-19")

    def test_get_email_details(self, m):
        rr_response = {
            "id": "1",
            "for_zaak": "https://zaken.nl/api/v1/zaak/123",
            "review_type": "advice",
            "requester": "Pietje",
        }
        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests/1",
            json=rr_response,
        )

        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"].update(
            {
                "kownslFrontendUrl": serialize_variable("a-url.test"),
                "deadline": serialize_variable("2020-04-01"),
            }
        )

        task = ExternalTask.objects.create(
            **task_dict,
        )

        email_details = get_email_details(task)
        self.assertTrue("email" in email_details)
        self.assertEqual(
            email_details["email"],
            {
                "subject": "Uw advies wordt gevraagd",
                "content": "",
            },
        )

        reminder = datetime.datetime.now() + datetime.timedelta(
            days=1
        ) >= datetime.datetime(2020, 4, 20, 0, 0, 0)
        self.assertEqual(
            email_details["context"],
            {
                "deadline": "2020-04-01",
                "kownslFrontendUrl": "a-url.test",
                "reminder": reminder,
            },
        )

        self.assertTrue("template" in email_details)
        self.assertEqual(email_details["template"], "advies")

        self.assertTrue("senderUsername" in email_details)
        self.assertEqual(email_details["senderUsername"], ["Pietje"])

    def test_setting_review_request_metadata(self, m):
        kownsl_id = str(uuid.uuid4())
        m.patch(
            f"https://kownsl.nl/api/v1/review-requests/{kownsl_id}", status_code=200
        )
        task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "kownslReviewRequestId": serialize_variable(kownsl_id),
                "metadata": serialize_variable(
                    {"key1": "value1", "nested": {"key": "value"}}
                ),
            },
        )

        result = set_review_request_metadata(task)

        self.assertEqual(result, {})
        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(m.last_request.method, "PATCH")
        self.assertEqual(
            m.last_request.json(),
            {
                "metadata": {"key1": "value1", "nested": {"key": "value"}},
            },
        )

    def test_get_approval_toelichtingen(self, m):
        approvals = [
            {
                "toelichting": "Beste voorstel ooit.",
            },
            {
                "toelichting": "Echt niet mee eens.",
            },
            {
                "toelichting": "",
            },
        ]
        m.get(f"{KOWNSL_API_ROOT}api/v1/review-requests/1/approvals", json=approvals)

        task = ExternalTask.objects.create(
            **self.task_dict,
        )

        result = get_approval_toelichtingen(task)
        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(
            result,
            {"toelichtingen": "Beste voorstel ooit.\n\nEcht niet mee eens.\n\nGeen"},
        )
