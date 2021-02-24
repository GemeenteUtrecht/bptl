from django.urls import reverse_lazy

import requests_mock
from django_webtest import WebTest
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.accounts.tests.factories import SuperUserFactory
from bptl.credentials.tests.factories import AppServiceCredentialsFactory
from bptl.tasks.models import TaskMapping
from bptl.tasks.tests.factories import DefaultServiceFactory

XENTIAL_API_ROOT = "https://xential.nl/api/"


@requests_mock.Mocker()
class XentialAdminTests(WebTest):
    url = reverse_lazy("xential:templates")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMapping.objects.create(
            topic_name="xential-topic",
        )
        xential = Service.objects.create(
            label="xential",
            api_type=APITypes.orc,
            api_root=XENTIAL_API_ROOT,
            auth_type=AuthTypes.api_key,
            oas="",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service=xential,
            alias="xential",
        )
        AppServiceCredentialsFactory.create(
            app__app_id="some-app-id",
            service=xential,
            header_key="Authorization",
            header_value="Basic aGVsbG86dGhpc2lzbm90YXNlY3JldA==",
        )

    def test_list_templates_context(self, m):
        user = SuperUserFactory.create()

        m.post(
            f"{XENTIAL_API_ROOT}auth/whoami",
            json={
                "user": {
                    "uuid": "a4664ccb-259e-4107-b800-d8e5a764b9dd",
                    "userName": "testuser",
                },
                "XSessionId": "f7f588eb-b7c9-4d23-babd-4a98a9326367",
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}template_utils/getUsableTemplates",
            json={
                "objects": [
                    {
                        "uuid": "uuid-1",
                        "objectTypeId": "templategroup",
                        "fields": [{"name": "name", "value": "Sjablonen"}],
                    }
                ]
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}template_utils/getUsableTemplates?parentGroupUuid=uuid-1",
            json={
                "objects": [
                    {
                        "uuid": "uuid-2",
                        "objectTypeId": "ooxmltexttemplate",
                        "fields": [{"name": "name", "value": "TestSjabloon"}],
                    }
                ]
            },
        )

        page = self.app.get(self.url, user=user)

        self.assertEqual(page.status_code, 200)
        self.assertIn("template_groups", page.context)

        template_group_context = page.context["template_groups"]

        self.assertEqual(1, len(template_group_context))

        template_group = template_group_context[0]

        self.assertEqual("Sjablonen", template_group["name"])
        self.assertEqual(1, len(template_group["templates"]))

        template = template_group["templates"][0]

        self.assertEqual("TestSjabloon", template["name"])
        self.assertEqual("uuid-2", template["uuid"])

    def test_list_templates_context_no_names(self, m):
        user = SuperUserFactory.create()

        m.post(
            f"{XENTIAL_API_ROOT}auth/whoami",
            json={
                "user": {
                    "uuid": "a4664ccb-259e-4107-b800-d8e5a764b9dd",
                    "userName": "testuser",
                },
                "XSessionId": "f7f588eb-b7c9-4d23-babd-4a98a9326367",
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}template_utils/getUsableTemplates",
            json={
                "objects": [
                    {"uuid": "uuid-1", "objectTypeId": "templategroup", "fields": []}
                ]
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}template_utils/getUsableTemplates?parentGroupUuid=uuid-1",
            json={
                "objects": [
                    {
                        "uuid": "uuid-2",
                        "objectTypeId": "ooxmltexttemplate",
                        "fields": [],
                    }
                ]
            },
        )

        page = self.app.get(self.url, user=user)

        self.assertEqual(page.status_code, 200)
        self.assertIn("template_groups", page.context)

        template_group_context = page.context["template_groups"]

        self.assertEqual(1, len(template_group_context))

        template_group = template_group_context[0]

        self.assertEqual("Geen naam", template_group["name"])
        self.assertEqual(1, len(template_group["templates"]))

        template = template_group["templates"][0]

        self.assertEqual("Geen naam", template["name"])
        self.assertEqual("uuid-2", template["uuid"])

    def test_list_templates_context_no_template_groups(self, m):
        user = SuperUserFactory.create()

        m.post(
            f"{XENTIAL_API_ROOT}auth/whoami",
            json={
                "user": {
                    "uuid": "a4664ccb-259e-4107-b800-d8e5a764b9dd",
                    "userName": "testuser",
                },
                "XSessionId": "f7f588eb-b7c9-4d23-babd-4a98a9326367",
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}template_utils/getUsableTemplates",
            json={"objects": []},
        )

        page = self.app.get(self.url, user=user)

        self.assertEqual(page.status_code, 200)
        self.assertIn("template_groups", page.context)

        template_group_context = page.context["template_groups"]

        self.assertEqual(0, len(template_group_context))

    def test_list_templates_context_no_templates_in_group(self, m):
        user = SuperUserFactory.create()

        m.post(
            f"{XENTIAL_API_ROOT}auth/whoami",
            json={
                "user": {
                    "uuid": "a4664ccb-259e-4107-b800-d8e5a764b9dd",
                    "userName": "testuser",
                },
                "XSessionId": "f7f588eb-b7c9-4d23-babd-4a98a9326367",
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}template_utils/getUsableTemplates",
            json={
                "objects": [
                    {
                        "uuid": "uuid-1",
                        "objectTypeId": "templategroup",
                        "fields": [{"name": "name", "value": "Sjablonen"}],
                    }
                ]
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}template_utils/getUsableTemplates?parentGroupUuid=uuid-1",
            json={"objects": []},
        )

        page = self.app.get(self.url, user=user)

        self.assertEqual(page.status_code, 200)
        self.assertIn("template_groups", page.context)

        template_group_context = page.context["template_groups"]

        self.assertEqual(1, len(template_group_context))

        template_group = template_group_context[0]

        self.assertEqual("Sjablonen", template_group["name"])
        self.assertEqual(0, len(template_group["templates"]))

    def test_rendering_as_table(self, m):
        user = SuperUserFactory.create()

        m.post(
            f"{XENTIAL_API_ROOT}auth/whoami",
            json={
                "user": {
                    "uuid": "a4664ccb-259e-4107-b800-d8e5a764b9dd",
                    "userName": "testuser",
                },
                "XSessionId": "f7f588eb-b7c9-4d23-babd-4a98a9326367",
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}template_utils/getUsableTemplates",
            json={
                "objects": [
                    {
                        "uuid": "uuid-1",
                        "objectTypeId": "templategroup",
                        "fields": [{"name": "name", "value": "Sjablonen"}],
                    }
                ]
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}template_utils/getUsableTemplates?parentGroupUuid=uuid-1",
            json={
                "objects": [
                    {
                        "uuid": "uuid-2",
                        "objectTypeId": "ooxmltexttemplate",
                        "fields": [{"name": "name", "value": "TestSjabloon"}],
                    }
                ]
            },
        )

        page = self.app.get(self.url, user=user)

        self.assertEqual("Template Group Sjablonen", page.html.h2.text)
        self.assertIn("Template name", page.html.table.thead.tr.text)
        self.assertIn("UUID", page.html.table.thead.tr.text)
        self.assertIn("TestSjabloon", page.html.table.tbody.tr.text)
        self.assertIn("uuid-2", page.html.table.tbody.tr.text)
