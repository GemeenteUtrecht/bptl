from unittest.mock import patch

from django.urls import reverse, reverse_lazy

from django_webtest import WebTest
from zgw_consumers.constants import APITypes

from bptl.accounts.tests.factories import SuperUserFactory
from bptl.tasks.tests.factories import ServiceFactory

from .factories import AppFactory


class AppCreateAdminTests(WebTest):
    url = reverse_lazy("admin:credentials_app_add")

    def test_app_create_no_autorisaties_api(self):
        user = SuperUserFactory.create()

        page = self.app.get(self.url, user=user)

        self.assertEqual(page.status_code, 200)
        self.assertNotIn(
            "autorisaties_application",
            page.form.fields,
        )

    @patch("bptl.credentials.forms.get_paginated_results")
    def test_app_create_with_autorisaties_api(self, m_get_paginated_results):
        ac1, ac2 = ServiceFactory.create_batch(2, api_type=APITypes.ac)
        apps = [
            [{"label": "app1", "url": "https://ac1.nl/api/v1/applicaties/123"}],
            [{"label": "app2", "url": "https://ac2.nl/api/v1/applicaties/456"}],
        ]
        user = SuperUserFactory.create()
        call_index = 0

        def side_effect(c, r):
            nonlocal call_index
            index = call_index % 2
            call_index += 1
            return apps[index]

        m_get_paginated_results.side_effect = side_effect

        page = self.app.get(self.url, user=user)

        self.assertEqual(page.status_code, 200)
        self.assertIn(
            "autorisaties_application",
            page.form.fields,
        )

        self.assertEqual(
            page.form["autorisaties_application"].options[1],
            ("https://ac1.nl/api/v1/applicaties/123", False, "app1"),
        )
        self.assertEqual(
            page.form["autorisaties_application"].options[2],
            ("https://ac2.nl/api/v1/applicaties/456", False, "app2"),
        )


class AppEditAdminTests(WebTest):
    @patch("bptl.credentials.forms.get_paginated_results")
    def test_app_change_with_autorisaties_api(self, m_get_paginated_results):
        ServiceFactory.create(api_type=APITypes.ac)
        apps = [
            {"label": "app1", "url": "https://ac.nl/api/v1/applicaties/123"},
            {"label": "app2", "url": "https://ac.nl/api/v1/applicaties/456"},
        ]
        m_get_paginated_results.return_value = apps
        user = SuperUserFactory.create()
        app = AppFactory.create(app_id="https://ac.nl/api/v1/applicaties/456")
        url = reverse("admin:credentials_app_change", args=(app.id,))

        change_page = self.app.get(url, user=user)

        self.assertEqual(change_page.status_code, 200)

        self.assertEqual(
            change_page.form["autorisaties_application"].options[1],
            ("https://ac.nl/api/v1/applicaties/123", False, "app1"),
        )
        self.assertEqual(
            change_page.form["autorisaties_application"].options[2],
            ("https://ac.nl/api/v1/applicaties/456", True, "app2"),
        )
