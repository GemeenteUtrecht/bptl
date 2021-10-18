import copy
import os
import uuid

from django.core.cache import caches
from django.test import TestCase, override_settings

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.cache import install_schema_fetcher_cache
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.credentials.tests.factories import AppServiceCredentialsFactory
from bptl.tasks.models import TaskMapping
from bptl.tasks.tests.factories import DefaultServiceFactory

from ..tasks import (
    get_approval_toelichtingen,
    get_client,
    get_email_details,
    get_review_request,
    get_review_request_reminder_date,
    get_review_response_status,
    set_review_request_metadata,
)

KOWNSL_API_ROOT = "https://kownsl.nl/"

MOCK_FILES_DIR = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    "schemas",
)


@requests_mock.Mocker()
@override_settings(ZGW_CONSUMERS_TEST_SCHEMA_DIRS=[MOCK_FILES_DIR])
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

    def setUp(self):
        super().setUp()

        # installs new, empty cache instance for each test
        install_schema_fetcher_cache()
        for cache in caches.all():
            cache.clear()

    def test_get_client_old_auth(self, m):
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

    def test_client_auth(self, m):
        task_kwargs = copy.deepcopy(self.task_dict)
        task_kwargs["variables"]["bptlAppId"] = serialize_variable("some-app-id")
        task = ExternalTask.objects.create(**task_kwargs)
        AppServiceCredentialsFactory.create(
            app__app_id="some-app-id",
            service=self.service,
            header_key="Other-Header",
            header_value="foobarbaz",
        )

        client = get_client(task)

        self.assertIsNone(client.auth)
        self.assertEqual(client.auth_header, {"Other-Header": "foobarbaz"})

    def test_get_review_request(self, m):
        mock_service_oas_get(m, KOWNSL_API_ROOT, "kownsl")
        task = ExternalTask.objects.create(
            **self.task_dict,
        )

        response = {
            "id": "1",
            "forZaak": "https://zaken.nl/api/v1/zaak/123",
            "reviewType": "advice",
        }
        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests/1",
            json=response,
        )

        review_requests = get_review_request(task)
        self.assertEqual(review_requests["id"], "1")

    def test_get_review_response_status(self, m):
        mock_service_oas_get(m, KOWNSL_API_ROOT, "kownsl")
        rr_response = {
            "id": "1",
            "forZaak": "https://zaken.nl/api/v1/zaak/123",
            "reviewType": "advice",
        }
        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests/1",
            json=rr_response,
        )

        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["kownslUsers"] = serialize_variable(
            ["user:zeus", "user:poseidon", "user:hades"]
        )

        task = ExternalTask.objects.create(
            **task_dict,
        )

        advice_response = [
            {
                "author": {"username": "zeus"},
                "group": "",
            },
            {
                "author": {"username": "poseidon"},
                "group": "",
            },
        ]

        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests/1/advices", json=advice_response
        )

        remindThese = get_review_response_status(task)
        self.assertTrue(remindThese["remindThese"][0], "Hades")

    def test_get_review_request_reminder_date(self, m):
        mock_service_oas_get(m, KOWNSL_API_ROOT, "kownsl")
        rr_response = {
            "id": "1",
            "forZaak": "https://zaken.nl/api/v1/zaak/123",
            "reviewType": "advice",
            "userDeadlines": {
                "user:zeus": "2020-04-20",
                "user:poseidon": "2020-04-20",
                "user:hades": "2020-04-20",
                "user:hera": "2021-04-20",
                "user:demeter": "2021-04-20",
            },
        }
        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests/1",
            json=rr_response,
        )

        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["kownslUsers"] = serialize_variable(
            ["user:zeus", "user:poseidon", "user:hades"]
        )

        task = ExternalTask.objects.create(
            **task_dict,
        )

        reminderDate = get_review_request_reminder_date(task)
        self.assertEqual(reminderDate["reminderDate"], "2020-04-19")

    def test_get_email_details(self, m):
        mock_service_oas_get(m, KOWNSL_API_ROOT, "kownsl")
        rr_response = {
            "id": "1",
            "forZaak": "https://zaken.nl/api/v1/zaak/123",
            "reviewType": "advice",
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

        self.assertEqual(
            email_details["context"],
            {
                "deadline": "2020-04-01",
                "kownslFrontendUrl": "a-url.test",
            },
        )

        self.assertTrue("template" in email_details)
        self.assertEqual(email_details["template"], "advies")

        self.assertTrue("senderUsername" in email_details)
        self.assertEqual(email_details["senderUsername"], ["Pietje"])

    def test_setting_review_request_metadata(self, m):
        mock_service_oas_get(m, KOWNSL_API_ROOT, "kownsl")
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
        self.assertEqual(len(m.request_history), 2)  # 1 for client schema
        self.assertEqual(m.last_request.method, "PATCH")
        self.assertEqual(
            m.last_request.json(),
            {
                "metadata": {"key1": "value1", "nested": {"key": "value"}},
            },
        )

    def test_get_approval_toelichtingen(self, m):
        mock_service_oas_get(m, KOWNSL_API_ROOT, "kownsl")
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
        self.assertEqual(len(m.request_history), 2)  # one for client schema
        self.assertEqual(
            result,
            {"toelichtingen": "Beste voorstel ooit.\n\nEcht niet mee eens.\n\nGeen"},
        )
