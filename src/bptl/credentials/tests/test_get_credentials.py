from django.test import TestCase

import jwt
from zgw_consumers.constants import APITypes, AuthTypes

from bptl.work_units.zgw.tests.factories import ServiceFactory

from ..api import get_credentials
from .factories import AppFactory, AppServiceCredentialsFactory


class GetCredentialsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.svc_x = ServiceFactory.create(
            label="service X",
            api_type=APITypes.zrc,
            auth_type=AuthTypes.zgw,
        )
        cls.svc_y = ServiceFactory.create(
            label="service Y",
            api_type=APITypes.drc,
            auth_type=AuthTypes.zgw,
        )
        cls.svc_a = ServiceFactory.create(
            label="service A",
            api_type=APITypes.orc,
            auth_type=AuthTypes.api_key,
        )

    def test_get_credentials_subset(self):
        app = AppFactory.create()
        AppServiceCredentialsFactory.create(
            app=app,
            service=self.svc_x,
            client_id="x-marks-the-spot",
            secret="supersecret",
        )
        AppServiceCredentialsFactory.create(
            app=app,
            service=self.svc_y,
            client_id="y-marks-the-spot",
            secret="supersecret",
        )
        AppServiceCredentialsFactory.create(
            app=app,
            service=self.svc_a,
            header_key="Api-Key",
            header_value="blelele",
        )

        result = get_credentials(app.app_id, self.svc_x, self.svc_a)

        a_credentials = result[self.svc_a]
        self.assertEqual(a_credentials, {"Api-Key": "blelele"})

        x_credentials = result[self.svc_x]
        self.assertEqual(list(x_credentials.keys()), ["Authorization"])
        bearer = x_credentials["Authorization"]
        self.assertTrue(bearer.startswith("Bearer "))
        _, token = bearer.split(" ")
        try:
            payload = jwt.decode(token, "supersecret", algorithms=["HS256"])
        except Exception:
            self.fail("Invalid JWT generated")

        self.assertEqual(payload["client_id"], "x-marks-the-spot")
