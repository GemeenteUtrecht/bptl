from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable

from bptl.camunda.tests.factories import ExternalTaskFactory

from ..handlers import on_package_complete
from ..models import CreatedPackage


class HandlerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.task = ExternalTaskFactory.create(instance_id="some-instance-id")
        CreatedPackage.objects.create(package_id="somePackageId", task=cls.task)

    @requests_mock.Mocker()
    def test_package_complete_no_message_id(self, m):
        on_package_complete("somePackageId")

        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_package_complete_send_bpmn_message(self, m):
        self.task.variables = {"messageId": serialize_variable("package_completed")}
        self.task.save()
        m.post("https://camunda.example.com/engine-rest/message")

        on_package_complete("somePackageId")

        self.assertEqual(m.call_count, 1)
        self.assertEqual(m.last_request.method, "POST")
        self.assertEqual(
            m.last_request.json(),
            {
                "messageName": "package_completed",
                "processInstanceId": "some-instance-id",
                "processVariables": {},
            },
        )
