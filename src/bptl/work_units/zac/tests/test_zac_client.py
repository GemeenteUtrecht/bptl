from django.test import TestCase

import requests_mock

from bptl.work_units.zac.client import ZACClient
from bptl.work_units.zac.models import ZACConfig

ZAC_API_ROOT = "https://zac.example.com/"
FILTER_USERS_URL = (
    f"{ZAC_API_ROOT}accounts/api/users?filter_users=thor,loki&Include=True"
)


@requests_mock.Mocker()
class ZacTaskTests(TestCase):
    client_class = ZACClient

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        config = ZACConfig.get_solo()
        config.api_root = ZAC_API_ROOT
        config.header_key = "Authorization"
        config.header_value = (
            "Token ThisIsNotTheGreatestTokenInTheWorldThisIsJustATribute"
        )
        config.save()

    def test_client(self, m):
        self.assertIsInstance(self.client.config.auth_header, dict)
        self.assertTrue("Authorization" in self.client.config.auth_header)
        self.assertEqual(
            self.client.config.auth_header["Authorization"],
            "Token ThisIsNotTheGreatestTokenInTheWorldThisIsJustATribute",
        )

        m.get(ZAC_API_ROOT, json={})

        response = self.client.get("")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("Authorization" in m.request_history[0].headers)
        self.assertEqual(
            m.request_history[0].headers["Authorization"],
            "Token ThisIsNotTheGreatestTokenInTheWorldThisIsJustATribute",
        )
