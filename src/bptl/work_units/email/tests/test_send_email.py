import copy

from django.core import mail
from django.test import TestCase

from rest_framework.exceptions import ValidationError

from bptl.camunda.models import ExternalTask

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
                    "value": '{"subject": "Vakantiepret","content": "Dit is pas leuk."}',
                    "valueInfo": {},
                },
                "template": {
                    "type": "String",
                    "value": "generiek",
                    "valueInfo": {},
                },
                "kwargs": {
                    "type": "Json",
                    "value": '{"reminder": "True", "deadline": "2020-04-20 16:20", "kownslFrontendUrl":"test.com"}',
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
            """Beste Jan Janssen,\n\nDit is pas leuk.\n\nMet vriendelijke groeten,\n\nKees Koos""",
        )
        self.assertEqual(email.subject, "HERINNERING: Vakantiepret")
        self.assertEqual(email.to, ["jan.janssen@test.test"])

    def test_send_email_missing_variable(self):
        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"].pop("receiver")
        task = ExternalTask.objects.create(**task_dict)
        send_mail = SendEmailTask(task)

        with self.assertRaises(Exception) as e:
            send_mail.perform()

        self.assertEqual(type(e.exception), ValidationError)
        self.assertTrue("Dit veld is vereist." in str(e.exception))

    def test_send_email_review_template(self):
        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["template"] = {
            "type": "String",
            "value": "advies",
            "valueInfo": {},
        }
        task = ExternalTask.objects.create(**task_dict)
        send_mail = SendEmailTask(task)
        send_mail.perform()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertEqual(
            email.body,
            """Beste Jan Janssen,

HERINNERING: Uw advies is vereist. U heeft tot 20 april 2020 16:20 om te reageren.

Klik alstublieft <a href="test.com">hier</a>.

Dit is pas leuk.

Met vriendelijke groeten,

Kees Koos""",
        )
        self.assertEqual(email.subject, "HERINNERING: Vakantiepret")
        self.assertEqual(email.to, ["jan.janssen@test.test"])

    def test_send_email_invalid_review_template(self):
        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["template"] = {
            "type": "String",
            "value": "lelijk",
            "valueInfo": {},
        }
        task = ExternalTask.objects.create(**task_dict)
        send_mail = SendEmailTask(task)

        with self.assertRaises(Exception) as e:
            send_mail.perform()

        self.assertEqual(type(e.exception), ValidationError)
        self.assertTrue('"lelijk" is een ongeldige keuze.' in str(e.exception))
