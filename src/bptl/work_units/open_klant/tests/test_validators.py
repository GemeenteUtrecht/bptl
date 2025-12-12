from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from bptl.work_units.open_klant.validators import RFC5322EmailValidator


class RFC5322EmailValidatorTests(SimpleTestCase):

    def setUp(self):
        self.validator = RFC5322EmailValidator()

    def test_allows_ampersand_email(self):
        self.validator("blabla&blabla@blabla.nl")

    def test_strips_whitespace(self):
        self.validator("  blabla&blabla@blabla.nl  ")

    def test_rejects_none(self):
        with self.assertRaises(ValidationError):
            self.validator(None)

    def test_rejects_invalid_email(self):
        with self.assertRaises(ValidationError):
            self.validator("not-an-email")

    def test_rejects_display_name_addr_spec(self):
        with self.assertRaises(ValidationError):
            self.validator("Name <foo@example.com>")
