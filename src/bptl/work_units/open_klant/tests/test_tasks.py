from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from bptl.openklant.exceptions import EmailSendFailedException, OpenKlantEmailException
from bptl.work_units.open_klant.tasks import NotificeerBetrokkene


class NotificeerBetrokkeneTests(SimpleTestCase):

    def make_task(self, variables=None):
        task = SimpleNamespace()
        task.variables = variables or {}
        task.status = None
        task.saved = []
        task.save = lambda update_fields=None: task.saved.append(update_fields)
        return task

    @patch(
        "bptl.work_units.open_klant.tasks.get_openklant_client",
        return_value=SimpleNamespace(),
    )
    @patch(
        "bptl.work_units.open_klant.tasks.get_actor_email_from_interne_taak",
        return_value="bad@@mail",
    )
    @patch("bptl.work_units.open_klant.tasks.RFC5322EmailValidator")
    def test_invalid_email_marks_failed(
        self, mock_validator, _mock_get_actor, _mock_client
    ):
        mock_validator.return_value.side_effect = ValidationError("invalid")

        task = self.make_task()
        wu = NotificeerBetrokkene(task=task)

        with self.assertRaises(OpenKlantEmailException):
            wu._get_and_validate_email_address()

        self.assertEqual(task.status, "failed")
        self.assertIn(["status"], task.saved)

    def test_send_email_success(self):
        task = self.make_task()
        wu = NotificeerBetrokkene(task=task)

        email = SimpleNamespace(send=lambda fail_silently=False: True)
        wu._send_email(email)

        self.assertEqual(task.status, "success")
        self.assertIn(["status"], task.saved)

    def test_send_email_failure(self):
        task = self.make_task()
        wu = NotificeerBetrokkene(task=task)

        email = SimpleNamespace(send=lambda fail_silently=False: False)

        with self.assertRaises(EmailSendFailedException):
            wu._send_email(email)

        self.assertEqual(task.status, "failed")
        self.assertIn(["status"], task.saved)
