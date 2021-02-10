from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable

from bptl.camunda.tests.factories import ExternalTaskFactory

from ..handlers import on_document_created
from ..models import XentialTicket


class HandlerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.task = ExternalTaskFactory.create(instance_id="some-instance-id")
        XentialTicket.objects.create(
            task=cls.task,
            bptl_ticket_uuid="2d30f19b-8666-4f45-a8da-78ad7ed0ef4d",
            ticket_uuid="f15aceb4-b316-45bc-8353-7906ae125557",
        )

    @requests_mock.Mocker()
    def test_document_created_no_message_id(self, m):
        on_document_created(self.task, "http://example.com/doc/doc-uuid")

        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_document_created_sends_message(self, m):
        self.task.variables = {"messageId": serialize_variable("Document created!")}
        self.task.save()
        m.post("https://camunda.example.com/engine-rest/message")

        on_document_created(self.task, "http://example.com/doc/doc-uuid")

        self.assertEqual(m.call_count, 1)
        self.assertEqual(m.last_request.method, "POST")
        self.assertEqual(
            m.last_request.json(),
            {
                "messageName": "Document created!",
                "processInstanceId": "some-instance-id",
                "processVariables": {
                    "url": {
                        "type": "String",
                        "value": "http://example.com/doc/doc-uuid",
                    }
                },
            },
        )
