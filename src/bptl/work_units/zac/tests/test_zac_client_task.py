import json

from django.test import TestCase

import requests_mock

from bptl.camunda.models import ExternalTask
from bptl.tasks.base import MissingVariable
from bptl.work_units.zac.models import ZACConfig
from bptl.work_units.zac.tasks import UserDetailsTask

ZAC_API_ROOT = "https://zac.example.com/"
FILTER_USERS_URL = (
    f"{ZAC_API_ROOT}accounts/api/users?filter_users=thor,loki&Include=True"
)


@requests_mock.Mocker()
class ZacTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.task_dict = {
            "topic_name": "send-email",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "kownslUsers": {
                    "type": "Json",
                    "value": '["thor", "loki"]',
                    "valueInfo": {},
                },
            },
        }
        cls.task = ExternalTask.objects.create(
            **cls.task_dict,
        )

        config = ZACConfig.get_solo()
        config.api_root = ZAC_API_ROOT
        config.save()

    def test_get_user_details_happy(self, m):
        zac_mock_data = {
            "count": 2,
            "results": [
                {
                    "id": "1",
                    "username": "thor",
                    "firstName": "Thor",
                    "lastName": "Odinson",
                    "email": "thor@odinson.no",
                    "isAwesome": "true",
                },
                {
                    "id": "3",
                    "username": "loki",
                    "firstName": "Loki",
                    "lastName": "Laufeyson",
                    "email": "loki@laufeyson.no",
                    "isLiar": "true",
                },
            ],
        }
        m.get(FILTER_USERS_URL, json=zac_mock_data)

        task = UserDetailsTask(self.task)
        response = task.get_client_response()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), zac_mock_data)

        cleaned_data = json.loads(task.perform())
        self.assertEqual(len(cleaned_data), 2)
        for user in cleaned_data:
            self.assertTrue("name" in user)
            self.assertTrue("email" in user)

    def test_get_user_details_missing_first_and_last_names(self, m):
        zac_mock_data = {
            "count": 2,
            "results": [
                {
                    "id": "1",
                    "username": "thor",
                    "firstName": "",
                    "lastName": "",
                    "email": "thor@odinson.no",
                    "isAwesome": "true",
                },
                {
                    "id": "3",
                    "username": "loki",
                    "firstName": "",
                    "lastName": "",
                    "email": "loki@laufeyson.no",
                    "isLiar": "true",
                },
            ],
        }

        m.get(FILTER_USERS_URL, json=zac_mock_data)
        task = UserDetailsTask(self.task)
        cleaned_data = json.loads(task.perform())
        self.assertEqual(len(cleaned_data), 2)
        for user in cleaned_data:
            self.assertEqual(user["name"], "Medewerker")

    def test_get_user_details_missing_first_and_last_names_alternatively(self, m):
        zac_mock_data = {
            "count": 2,
            "results": [
                {
                    "id": "1",
                    "username": "thor",
                    "firstName": "",
                    "lastName": "Odinson",
                    "email": "thor@odinson.no",
                    "isAwesome": "true",
                },
                {
                    "id": "3",
                    "username": "loki",
                    "firstName": "Loki",
                    "lastName": "",
                    "email": "loki@laufeyson.no",
                    "isLiar": "true",
                },
            ],
        }

        m.get(FILTER_USERS_URL, json=zac_mock_data)
        task = UserDetailsTask(self.task)
        cleaned_data = json.loads(task.perform())
        self.assertEqual(len(cleaned_data), 2)
        for user in cleaned_data:
            if user["firstName"] == "loki":
                self.assertEqual(user["name"], "Loki")
            elif user["lastName"] == "Odinson":
                self.assertEqual(user["name"], "Odinson")

    def test_get_user_details_missing_email(self, m):
        zac_mock_data = {
            "count": 2,
            "results": [
                {
                    "id": "1",
                    "username": "thor",
                    "firstName": "",
                    "lastName": "Odinson",
                    "email": "thor@odinson.no",
                    "isAwesome": "true",
                },
                {
                    "id": "3",
                    "username": "loki",
                    "firstName": "Loki",
                    "lastName": "",
                    "email": "",
                    "isLiar": "true",
                },
            ],
        }

        m.get(FILTER_USERS_URL, json=zac_mock_data)
        task = UserDetailsTask(self.task)
        with self.assertRaises(Exception) as e:
            task.perform()

        self.assertEqual(type(e.exception), MissingVariable)
        self.assertTrue("results" in e.exception.args[0])
        self.assertTrue("email" in e.exception.args[0]["results"][-1])
        self.assertTrue(
            "Dit veld mag niet leeg zijn."
            in e.exception.args[0]["results"][-1]["email"][0]
        )
