import copy
import datetime
import json

from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.camunda.models import ExternalTask
from bptl.tasks.models import TaskMapping
from bptl.work_units.kownsl.tasks import (
    get_client,
    get_email_details,
    get_review_request,
    get_review_request_reminder_date,
    get_review_response_status,
)
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory

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
                "zaakUrl": {
                    "type": "String",
                    "value": "https://zaken.nl/api/v1/zaak/123",
                    "valueInfo": {},
                },
                "reviewRequestId": {
                    "type": "String",
                    "value": "1",
                    "valueInfo": {},
                },
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

        response = [
            {
                "id": "1",
                "for_zaak": "https://zaken.nl/api/v1/zaak/123",
                "review_type": "advice",
            },
            {
                "id": "2",
                "for_zaak": "https://zaken.nl/api/v1/zaak/123",
                "review_type": "advice",
            },
        ]
        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests?for_zaak=https://zaken.nl/api/v1/zaak/123",
            json=response,
        )

        review_requests = get_review_request(task)

        request = review_requests
        self.assertEqual(request["id"], "1")
        self.assertEqual(
            m.last_request.qs["for_zaak"][0], "https://zaken.nl/api/v1/zaak/123"
        )

    def test_get_review_response_status(self, m):
        rr_response = [
            {
                "id": "1",
                "for_zaak": "https://zaken.nl/api/v1/zaak/123",
                "review_type": "advice",
            },
        ]
        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests?for_zaak=https://zaken.nl/api/v1/zaak/123",
            json=rr_response,
        )

        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["kownslUsers"] = {
            "type": "Json",
            "value": '["Zeus","Poseidon","Hades"]',
            "valueInfo": {},
        }

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
        rr_response = [
            {
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
            },
        ]
        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests?for_zaak=https://zaken.nl/api/v1/zaak/123",
            json=rr_response,
        )

        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["kownslUsers"] = {
            "type": "Json",
            "value": '["Zeus","Poseidon","Hades"]',
            "valueInfo": {},
        }

        task = ExternalTask.objects.create(
            **task_dict,
        )

        reminderDate = get_review_request_reminder_date(task)
        self.assertEqual(reminderDate["reminderDate"], "2020-04-19")

    def test_get_email_details(self, m):
        rr_response = [
            {
                "id": "1",
                "for_zaak": "https://zaken.nl/api/v1/zaak/123",
                "review_type": "advice",
                "requester": "Pietje",
            },
        ]
        m.get(
            f"{KOWNSL_API_ROOT}api/v1/review-requests?for_zaak=https://zaken.nl/api/v1/zaak/123",
            json=rr_response,
        )

        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"].update(
            {
                "kownslFrontendUrl": {
                    "type": "String",
                    "value": "a-url.test",
                    "valueInfo": {},
                },
                "deadline": {
                    "type": "String",
                    "value": "2020-04-01",
                    "valueInfo": {},
                },
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
