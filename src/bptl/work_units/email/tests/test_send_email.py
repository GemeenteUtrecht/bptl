from django.core import mail
from django.test import TestCase

from bptl.camunda.models import ExternalTask
from bptl.tasks.base import MissingVariable

from ..tasks import SendEmailTask


class SendEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.task_dict = {
            "topic_name": "send-email",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "sender": {
                    "type": "Json",
                    "value": '{"email":"kees.koos@test.test","name":"Kees Koos"}',
                    "valueInfo": {},
                },
                "receiver": {
                    "type": "Json",
                    "value": '{"email":"jan.janssen@test.test","name":"Jan Janssen"}',
                    "valueInfo": {},
                },
                "email": {
                    "type": "Json",
                    "value": '{"subject": "Vakantiepret","body": "Dit is pas leuk."}',
                    "valueInfo": {},
                },
            },
        }

    def test_send_email_happy(self):
        task = ExternalTask.objects.create(**self.task_dict)
        send_mail = SendEmailTask(task)
        send_mail.perform()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertEqual(
            email.body,
            """Dear Jan Janssen,

Dit is pas leuk.

Kind regards,

Kees Koos
""",
        )
        self.assertEqual(email.subject, "Vakantiepret")
        self.assertEqual(email.to, ["jan.janssen@test.test"])

    def test_send_email_missing_variable(self):
        task_dict = dict(self.task_dict)
        task_dict["variables"].pop("receiver")
        task = ExternalTask.objects.create(**task_dict)
        send_mail = SendEmailTask(task)

        with self.assertRaises(Exception) as e:
            send_mail.perform()

        self.assertEqual(type(e.exception), MissingVariable)
        self.assertTrue(
            "The variable receiver is missing or empty." in str(e.exception)
        )
