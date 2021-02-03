from datetime import timedelta

from django.test import TestCase, override_settings

from freezegun import freeze_time

from bptl.camunda.tests.factories import ExternalTaskFactory

from ..models import XentialTicket
from ..tokens import token_generator


@override_settings(XENTIAL_URL_TOKEN_TIMEOUT_DAYS=7)
class TokenInvalidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.task = ExternalTaskFactory.create(instance_id="some-instance-id")
        cls.ticket = XentialTicket.objects.create(
            task=cls.task,
            bptl_ticket_uuid="2d30f19b-8666-4f45-a8da-78ad7ed0ef4d",
            ticket_uuid="f15aceb4-b316-45bc-8353-7906ae125557",
            is_ticket_complete=False,
        )

    def test_valid_token(self):
        token = token_generator.make_token(self.ticket)

        for day in range(8):
            with self.subTest(day_offset=day):
                with freeze_time(timedelta(days=day)):
                    valid = token_generator.check_token(self.ticket, token)

                self.assertTrue(valid)

    def test_token_expired(self):
        token = token_generator.make_token(self.ticket)

        with freeze_time(timedelta(days=8)):
            valid = token_generator.check_token(self.ticket, token)

        self.assertFalse(valid)

    def test_token_invalidated_properties_changed(self):
        token = token_generator.make_token(self.ticket)

        self.ticket.is_ticket_complete = True
        self.ticket.save()

        valid = token_generator.check_token(self.ticket, token)

        self.assertFalse(valid)

    def test_wrong_format_token(self):

        valid = token_generator.check_token(self.ticket, "dummy")

        self.assertFalse(valid)

    def test_invalid_timestamp_b36(self):
        valid = token_generator.check_token(self.ticket, "$$$-blegh")

        self.assertFalse(valid)
