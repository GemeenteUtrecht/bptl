from django.urls import reverse_lazy

import requests_mock
from django_webtest import WebTest
from zgw_consumers.constants import APITypes

from bptl.accounts.tests.factories import SuperUserFactory
from bptl.tasks.tests.factories import DefaultServiceFactory, ServiceFactory

from ..client import ALIAS

XENTIAL_API_ROOT = "https://alfresco.nl/xential/s/"


@requests_mock.Mocker()
class XentialAdminTests(WebTest):
    url = reverse_lazy("xential:templates")

    def test_list_templates(self, m):
        user = SuperUserFactory.create()
        xential_service = ServiceFactory.create(
            api_root=XENTIAL_API_ROOT, api_type=APITypes.orc
        )
        DefaultServiceFactory.create(alias=ALIAS, service=xential_service)

        template_data = [
            {
                "templateName": "Interactief",
                "templateUuid": "64de49cf-0ae6-49b1-949c-c65b997d183b",
            },
            {
                "templateName": "Silent",
                "templateUuid": "9536db06-ca04-4b95-98fe-f1e708f3a90a",
            },
        ]
        m.get(
            f"{XENTIAL_API_ROOT}xential/templates",
            json={
                "data": {
                    "templates": template_data,
                    "params": {
                        "sessionId": "48a8393f-9030-4d71-848d-b3a00126cea3",
                        "uuid": "9cdfe02e-4a18-4f6c-8816-085b34a9c75c",
                    },
                }
            },
        )

        page = self.app.get(self.url, user=user)

        self.assertEqual(page.status_code, 200)
        self.assertEqual(
            page.context["template_groups"], {XENTIAL_API_ROOT: template_data}
        )
