from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.credentials.tests.factories import AppServiceCredentialsFactory
from bptl.tasks.models import BaseTask
from bptl.tasks.tests.factories import DefaultServiceFactory
from bptl.work_units.zac.client import get_client

ZAC_API_ROOT = "https://zac.example.com/"


@requests_mock.Mocker()
class ZacTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        zac = Service.objects.create(
            api_root=ZAC_API_ROOT,
            api_type=APITypes.orc,
            auth_type=AuthTypes.api_key,
            header_key="Authorization",
            header_value="Token ThisIsNotTheGreatestTokenInTheWorldThisIsJustATribute",
        )
        DefaultServiceFactory.create(
            task_mapping__topic_name="some-topic",
            service=zac,
            alias="zac",
        )
        AppServiceCredentialsFactory.create(
            app__app_id="some-app-id",
            service=zac,
            header_key="Other-Header",
            header_value="foobarbaz",
        )

    def test_client(self, m):
        task = BaseTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer": "999999011",
                "age": 18,
                "bptlAppId": "some-app-id",
            },
        )

        client = get_client(task)

        self.assertIsInstance(client.auth, dict)
        self.assertNotIn("Authorization", client.auth)
        self.assertEqual(
            client.auth["Other-Header"],
            "foobarbaz",
        )

        m.get(ZAC_API_ROOT, json={})

        response = client.get("")

        self.assertEqual(response.status_code, 200)
        self.assertTrue("Other-Header" in m.request_history[0].headers)
        self.assertEqual(
            m.request_history[0].headers["Other-Header"],
            "foobarbaz",
        )
