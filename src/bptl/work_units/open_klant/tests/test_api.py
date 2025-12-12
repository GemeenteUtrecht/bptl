from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from bptl.work_units.open_klant.api import (
    get_details_betrokkene,
    get_klantcontact_for_interne_taak,
)


class OpenKlantApiTests(SimpleTestCase):

    def test_get_klantcontact_uses_given_client(self):
        called = {}

        def retrieve(resource, url):
            called["resource"] = resource
            called["url"] = url
            return {"ok": True}

        client = SimpleNamespace(retrieve=retrieve)

        result = get_klantcontact_for_interne_taak("http://kc/1", client=client)

        self.assertEqual(result, {"ok": True})
        self.assertEqual(called["resource"], "klantcontact")

    @patch("bptl.work_units.open_klant.api.get_paginated_results")
    def test_get_details_betrokkene_collects_email_and_phone(self, mock_pages):
        mock_pages.return_value = [
            {"soortDigitaalAdres": "email", "adres": "a@example.com"},
            {"soortDigitaalAdres": "email", "adres": "b@example.com"},
            {"soortDigitaalAdres": "telefoonnummer", "adres": "0612345678"},
        ]

        client = SimpleNamespace(
            retrieve=lambda resource, url=None, **kwargs: {
                "volledigeNaam": "Jan Jansen"
            }
        )

        naam, email, telefoon = get_details_betrokkene("url", client=client)

        self.assertEqual(naam, "Jan Jansen")
        self.assertEqual(email, "a@example.com, b@example.com")
        self.assertEqual(telefoon, "0612345678")

    @patch("bptl.work_units.open_klant.api.get_paginated_results", return_value=[])
    def test_get_details_betrokkene_defaults_to_nb(self, _):
        client = SimpleNamespace(retrieve=lambda resource, url=None, **kwargs: {})

        naam, email, telefoon = get_details_betrokkene("url", client=client)

        self.assertEqual(naam, "N.B.")
        self.assertEqual(email, "N.B.")
        self.assertEqual(telefoon, "N.B.")
