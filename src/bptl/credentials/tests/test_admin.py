from unittest.mock import patch

from django.urls import reverse, reverse_lazy

from django_webtest import WebTest
from zgw_consumers.constants import APITypes

from bptl.accounts.tests.factories import SuperUserFactory
from bptl.credentials.tests.factories import AppFactory
from bptl.tasks.tests.factories import ServiceFactory


def get_admin_form(page):
    """
    Return the main Django admin form, skipping logout/search forms.
    """
    # Newer admin templates often have multiple <form>s:
    # logout-form, search, and the actual model form with id="app_form"
    if "app_form" in page.forms:
        return page.forms["app_form"]
    # fallback to the first non-logout form
    for key, form in page.forms.items():
        if key != "logout-form":
            return form
    raise AssertionError(f"No usable admin form found in {list(page.forms.keys())}")


class AppCreateAdminTests(WebTest):
    url = reverse_lazy("admin:credentials_app_add")

    def test_app_create_no_autorisaties_api(self):
        user = SuperUserFactory.create()
        page = self.app.get(self.url, user=user)
        self.assertEqual(page.status_code, 200)

        form = get_admin_form(page)
        self.assertNotIn("autorisaties_application", form.fields)

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

        form = get_admin_form(page)

        self.assertIn("autorisaties_application", form.fields)
        self.assertEqual(
            form["autorisaties_application"].options[1],
            ("https://ac1.nl/api/v1/applicaties/123", False, "app1"),
        )
        self.assertEqual(
            form["autorisaties_application"].options[2],
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

        form = get_admin_form(change_page)

        self.assertEqual(
            form["autorisaties_application"].options[1],
            ("https://ac.nl/api/v1/applicaties/123", False, "app1"),
        )
        self.assertEqual(
            form["autorisaties_application"].options[2],
            ("https://ac.nl/api/v1/applicaties/456", True, "app2"),
        )
