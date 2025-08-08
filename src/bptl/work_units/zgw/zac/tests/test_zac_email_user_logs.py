# from django.test import TestCase

# import requests_mock
# from django_camunda.utils import serialize_variable
# from rest_framework.serializers import ValidationError
# from zgw_consumers.constants import APITypes, AuthTypes

# from bptl.camunda.models import ExternalTask
# from bptl.tasks.base import MissingVariable
# from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

# from ..tasks import ZacEmailUserLogs

# ZAC_ROOT = "https://zac.example.com/"
# ZAC_LOG_URL = f"{ZAC_ROOT}api/accounts/management/axes/logs"


# class ZacEmailUserLogsTests(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         super().setUpTestData()

#         cls.task_dict = {
#             "topic_name": "some-topic-name",
#             "worker_id": "test-worker-id",
#             "task_id": "test-task-id",
#             "variables": {
#                 "recipientList": serialize_variable(["user@bptl.com"]),
#             },
#         }
#         cls.task_url = ExternalTask.objects.create(
#             **cls.task_dict,
#         )

#         mapping = TaskMappingFactory.create(topic_name="some-topic-name")
#         DefaultServiceFactory.create(
#             task_mapping=mapping,
#             service__api_root=ZAC_ROOT,
#             service__api_type=APITypes.orc,
#             service__auth_type=AuthTypes.no_auth,
#             alias="zac",
#         )

#     @requests_mock.Mocker()
#     def test_post_recipient_list_to_zac_endpoint(self, m):
#         m.post(ZAC_LOG_URL, status_code=204)

#         task = ZacEmailUserLogs(self.task_url)
#         response = task.perform()
#         self.assertEqual(response, None)

#         self.assertEqual(
#             m.last_request.url,
#             ZAC_LOG_URL,
#         )
#         self.assertEqual(m.last_request.method, "POST")
#         self.assertEqual(m.last_request.json(), {"recipientList": ["user@bptl.com"]})

#     def test_post_recipient_list_to_zac_endpoint_missing_variable(self):
#         task_dict = {**self.task_dict}
#         task_dict["variables"] = {}
#         task_url = ExternalTask.objects.create(
#             **task_dict,
#         )
#         task = ZacEmailUserLogs(task_url)
#         with self.assertRaises(Exception) as e:
#             task.perform()

#         self.assertEqual(type(e.exception), MissingVariable)
#         self.assertEqual(
#             e.exception.args[0], "The variable recipientList is missing or empty."
#         )

#     def test_post_recipient_list_to_zac_endpoint_empty_variable(self):
#         task_dict = {**self.task_dict}
#         task_dict["variables"] = {
#             "recipientList": serialize_variable([]),
#         }
#         task_url = ExternalTask.objects.create(
#             **task_dict,
#         )
#         task = ZacEmailUserLogs(task_url)
#         with self.assertRaises(Exception) as e:
#             task.perform()

#         self.assertEqual(type(e.exception), MissingVariable)
#         self.assertEqual(
#             e.exception.args[0], "The variable recipientList is missing or empty."
#         )

#     def test_post_recipient_list_to_zac_endpoint_wrong_format_email(self):
#         task_dict = {**self.task_dict}
#         task_dict["variables"] = {
#             "recipientList": serialize_variable(["asdsdss"]),
#         }
#         task_url = ExternalTask.objects.create(
#             **task_dict,
#         )
#         task = ZacEmailUserLogs(task_url)
#         with self.assertRaises(Exception) as e:
#             task.perform()

#         self.assertEqual(type(e.exception), ValidationError)
#         self.assertEqual(
#             e.exception.args[0]["recipientList"][0][0],
#             "Voer een geldig e-mailadres in.",
#         )
