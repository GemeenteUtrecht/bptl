from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from bptl.work_units.open_klant.mail import get_kcc_email_connection


class GetKCCEmailConnectionTests(SimpleTestCase):

    @patch("bptl.work_units.open_klant.mail.KCCEmailBackend")
    @patch("bptl.work_units.open_klant.mail.KCCEmailConfig")
    def test_connection_is_built_from_config(self, mock_config, mock_backend):
        mock_config.get_solo.return_value = SimpleNamespace(
            host="smtp.example.com",
            port=587,
            username="u",
            password="p",
            use_tls=True,
            use_ssl=False,
            timeout=10,
            from_email="from@example.com",
        )

        mock_backend.return_value = "BACKEND"

        backend = get_kcc_email_connection()

        self.assertEqual(backend, "BACKEND")
        mock_backend.assert_called_once()
