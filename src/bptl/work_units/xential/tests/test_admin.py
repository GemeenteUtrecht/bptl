from django_webtest import WebTest

from bptl.accounts.tests.factories import SuperUserFactory
from bptl.work_units.xential.models import XentialConfiguration

XENTIAL_CONFIG_URL = "/admin/xential/xentialconfiguration/"


class XentialConfigAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def test_config_callback(self):
        response = self.app.get(XENTIAL_CONFIG_URL, user=self.user)

        self.assertEqual(200, response.status_code)

        self.assertIn("Authentication key", response.text)
        self.assertIn("Callback URL", response.text)

    def test_change_authentication_key(self):
        response = self.app.get(XENTIAL_CONFIG_URL, user=self.user)
        form = response.form

        form["auth_key"] = "New-auth-key!"

        submission_response = form.submit().follow()

        self.assertEqual(200, submission_response.status_code)

        config = XentialConfiguration.get_solo()

        self.assertEqual("New-auth-key!", config.auth_key)
