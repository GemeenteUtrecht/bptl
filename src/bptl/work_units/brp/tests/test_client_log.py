from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.activiti.models import ServiceTask
from bptl.credentials.tests.factories import AppServiceCredentialsFactory
from bptl.tasks.tests.factories import DefaultServiceFactory

from ..tasks import IsAboveAge

BRP_API_ROOT = "http://brp.example.com/"
PERSON_URL = f"{BRP_API_ROOT}ingeschrevenpersonen/999999011?fields=leeftijd"


@requests_mock.Mocker()
class ZGWClientLogTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer": "999999011",
                "age": 18,
                "bptlAppId": "some-app-id",
            },
        )
        brp = Service.objects.create(
            api_root=BRP_API_ROOT,
            api_type=APITypes.orc,
            auth_type=AuthTypes.api_key,
            header_value="12345",
            header_key="X-Api-Key",
        )
        DefaultServiceFactory.create(
            task_mapping__topic_name="some-topic",
            service=brp,
            alias="brp",
        )
        AppServiceCredentialsFactory.create(
            app__app_id="some-app-id",
            service=brp,
            header_key="Other-Header",
            header_value="foobarbaz",
        )

    def test_log_client_retrieve(self, m):
        brp_mock_data = {"leeftijd": 36, "_links": {"self": {"href": PERSON_URL}}}
        m.get(PERSON_URL, json=brp_mock_data)

        task = IsAboveAge(self.fetched_task)
        task.perform()

        self.assertEqual(self.fetched_task.logs.count(), 1)

        log = self.fetched_task.logs.get()

        self.assertEqual(
            log.extra_data,
            {
                "request": {
                    "url": PERSON_URL,
                    "data": None,
                    "method": "GET",
                    "params": {"fields": ["leeftijd"]},
                    "headers": {
                        "Accept": "application/json",
                        "Connection": "keep-alive",
                        "User-Agent": "python-requests/2.26.0",
                        "Accept-Encoding": "gzip, deflate",
                        "Other-Header": "foobarbaz",
                    },
                },
                "response": {
                    "data": brp_mock_data,
                    "status": 200,
                    "headers": {},
                },
                "service_base_url": BRP_API_ROOT,
            },
        )
