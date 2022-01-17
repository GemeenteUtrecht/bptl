from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes

from bptl.camunda.models import ExternalTask
from bptl.tasks.base import MissingVariable
from bptl.tasks.tests.factories import DefaultServiceFactory

from ..tasks import UserDetailsTask

ZAC_API_ROOT = "https://zac.example.com/"
ZAC_USERS_URL = f"{ZAC_API_ROOT}api/accounts/users"


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
                "usernames": {
                    "type": "Json",
                    "value": '["user:thor", "user:loki"]',
                    "valueInfo": {},
                },
            },
        }
        cls.task_usernames = ExternalTask.objects.create(
            **cls.task_dict,
        )
        cls.task_emails = ExternalTask.objects.create(
            **{
                **cls.task_dict,
                "variables": {
                    "emailaddresses": {
                        "type": "Json",
                        "value": '["thor@email", "loki@email"]',
                        "valueInfo": {},
                    }
                },
            }
        )

        DefaultServiceFactory.create(
            task_mapping__topic_name="send-email",
            service__api_root=ZAC_API_ROOT,
            service__api_type=APITypes.orc,
            service__auth_type=AuthTypes.no_auth,
            alias="zac",
        )

    def test_get_user_details_from_usernames(self, m):
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
        m.get(ZAC_USERS_URL, json=zac_mock_data)

        task = UserDetailsTask(self.task_usernames)
        response = task.get_client_response()
        expected_response = [
            {
                "id": "1",
                "username": "thor",
                "firstName": "Thor",
                "lastName": "Odinson",
                "email": "thor@odinson.no",
                "isAwesome": "true",
                "assignee": "user:thor",
            },
            {
                "id": "3",
                "username": "loki",
                "firstName": "Loki",
                "lastName": "Laufeyson",
                "email": "loki@laufeyson.no",
                "isLiar": "true",
                "assignee": "user:loki",
            },
        ]
        self.assertEqual(response, expected_response)

        cleaned_data = task.perform()
        self.assertEqual(
            m.last_request.url,
            f"{ZAC_USERS_URL}?include_username=thor&include_username=loki",
        )
        self.assertEqual(len(cleaned_data["userData"]), 2)
        for user in cleaned_data["userData"]:
            self.assertTrue("name" in user)
            self.assertTrue("email" in user)

    def test_get_user_details_from_usernames_email_notifications(self, m):
        zac_mock_data = {
            "count": 1,
            "results": [
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
        m.get(ZAC_USERS_URL, json=zac_mock_data)
        task_notifications = {
            "topic_name": "send-email",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "usernames": serialize_variable(["user:thor", "user:loki"]),
                "emailNotificationList": serialize_variable(
                    {"user:thor": False, "user:loki": True}
                ),
            },
        }
        task_notifications = ExternalTask.objects.create(
            **task_notifications,
        )
        task = UserDetailsTask(task_notifications)
        response = task.get_client_response()
        expected_response = [
            {
                "id": "3",
                "username": "loki",
                "firstName": "Loki",
                "lastName": "Laufeyson",
                "email": "loki@laufeyson.no",
                "isLiar": "true",
                "assignee": "user:loki",
            }
        ]
        self.assertEqual(response, expected_response)
        self.assertEqual(m.last_request.url, f"{ZAC_USERS_URL}?include_username=loki")

    def test_get_user_details_from_emailaddresses(self, m):
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
        m.get(ZAC_USERS_URL, json=zac_mock_data)

        task = UserDetailsTask(self.task_emails)
        response = task.get_client_response()
        expected_response = [
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
        ]
        self.assertEqual(response, expected_response)

        cleaned_data = task.perform()
        self.assertEqual(
            m.last_request.url,
            f"{ZAC_USERS_URL}?include_email=thor%40email&include_email=loki%40email",
        )
        self.assertEqual(len(cleaned_data["userData"]), 2)
        for user in cleaned_data["userData"]:
            self.assertTrue("name" in user)
            self.assertTrue("username" in user)

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

        m.get(ZAC_USERS_URL, json=zac_mock_data)
        task = UserDetailsTask(self.task_usernames)
        cleaned_data = task.perform()
        self.assertEqual(
            m.last_request.url,
            f"{ZAC_USERS_URL}?include_username=thor&include_username=loki",
        )
        self.assertEqual(len(cleaned_data["userData"]), 2)
        for user in cleaned_data["userData"]:
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

        m.get(ZAC_USERS_URL, json=zac_mock_data)
        task = UserDetailsTask(self.task_usernames)
        cleaned_data = task.perform()
        self.assertEqual(
            m.last_request.url,
            f"{ZAC_USERS_URL}?include_username=thor&include_username=loki",
        )
        self.assertEqual(len(cleaned_data["userData"]), 2)
        for user in cleaned_data["userData"]:
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

        m.get(ZAC_USERS_URL, json=zac_mock_data)
        task = UserDetailsTask(self.task_usernames)
        with self.assertRaises(Exception) as e:
            task.perform()

        self.assertEqual(type(e.exception), MissingVariable)
        self.assertTrue("email" in e.exception.args[0][-1])
        self.assertTrue(
            "Dit veld mag niet leeg zijn." in e.exception.args[0][-1]["email"][0]
        )

    def test_get_user_details_missing_variables(self, m):
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

        m.get(ZAC_USERS_URL, json=zac_mock_data)
        task = ExternalTask.objects.create(**{**self.task_dict, "variables": {}})
        task = UserDetailsTask(task)
        with self.assertRaises(Exception) as e:
            task.perform()

        self.assertEqual(type(e.exception), MissingVariable)
        self.assertEqual(
            "Missing one of the required variables usernames or emailaddresses.",
            e.exception.args[0],
        )

    def test_get_user_details_from_groups_and_usernames_with_email_notifications(
        self, m
    ):
        zac_mock_data_user = {
            "count": 1,
            "results": [
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
        m.get(f"{ZAC_USERS_URL}?include_username=loki", json=zac_mock_data_user)
        zac_mock_data_group = {
            "count": 1,
            "results": [
                {
                    "id": "1",
                    "username": "thor",
                    "firstName": "",
                    "lastName": "Odinson",
                    "email": "thor@odinson.no",
                    "isAwesome": "true",
                },
            ],
        }
        m.get(f"{ZAC_USERS_URL}?include_groups=norse-gods", json=zac_mock_data_group)
        task = {
            "topic_name": "send-email",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "usernames": serialize_variable(["group:norse-gods", "user:loki"]),
                "emailNotificationList": serialize_variable(
                    {"user:loki": True, "group:norse-gods": True}
                ),
            },
        }
        task = ExternalTask.objects.create(
            **task,
        )
        task = UserDetailsTask(task)
        response = task.get_client_response()
        expected_response = [
            {
                "id": "3",
                "username": "loki",
                "firstName": "Loki",
                "lastName": "Laufeyson",
                "email": "loki@laufeyson.no",
                "isLiar": "true",
                "assignee": "user:loki",
            },
            {
                "id": "1",
                "username": "thor",
                "firstName": "",
                "lastName": "Odinson",
                "email": "thor@odinson.no",
                "isAwesome": "true",
                "assignee": "group:norse-gods",
            },
        ]
        self.assertEqual(response, expected_response)
        historical_urls = []
        for request in m.request_history:
            historical_urls.append(request.url)

        self.assertTrue(f"{ZAC_USERS_URL}?include_groups=norse-gods" in historical_urls)
        self.assertTrue(f"{ZAC_USERS_URL}?include_username=loki" in historical_urls)

        results = task.perform()
        expected_results = {
            "userData": [
                {
                    "email": "loki@laufeyson.no",
                    "firstName": "Loki",
                    "lastName": "Laufeyson",
                    "username": "loki",
                    "name": "Loki Laufeyson",
                    "assignee": "user:loki",
                },
                {
                    "email": "thor@odinson.no",
                    "firstName": "",
                    "lastName": "Odinson",
                    "username": "thor",
                    "name": "Odinson",
                    "assignee": "group:norse-gods",
                },
            ]
        }
        self.assertEqual(results, expected_results)

    def test_get_user_details_from_groups_with_email_notifications(self, m):
        zac_mock_data_group = {
            "count": 1,
            "results": [
                {
                    "id": "1",
                    "username": "thor",
                    "firstName": "",
                    "lastName": "Odinson",
                    "email": "thor@odinson.no",
                    "isAwesome": "true",
                },
            ],
        }
        m.get(ZAC_USERS_URL, json=zac_mock_data_group)
        task = {
            "topic_name": "send-email",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "usernames": serialize_variable(["group:norse-gods", "user:loki"]),
                "emailNotificationList": serialize_variable(
                    {"user:thor": False, "group:norse-gods": True}
                ),
            },
        }
        task = ExternalTask.objects.create(
            **task,
        )
        task = UserDetailsTask(task)
        response = task.get_client_response()
        expected_response = [
            {
                "id": "1",
                "username": "thor",
                "firstName": "",
                "lastName": "Odinson",
                "email": "thor@odinson.no",
                "isAwesome": "true",
                "assignee": "group:norse-gods",
            }
        ]
        self.assertEqual(response, expected_response)
        self.assertEqual(
            m.last_request.url, f"{ZAC_USERS_URL}?include_groups=norse-gods"
        )
