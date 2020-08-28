from django.test import TestCase

import requests_mock

from bptl.activiti.models import ServiceTask

from ..models import BRPConfig
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
            variables={"burgerservicenummer": "999999011", "age": 18},
        )

        config = BRPConfig.get_solo()
        config.api_root = BRP_API_ROOT
        config.save()

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
                    "params": {"fields": "leeftijd"},
                    "headers": {
                        "Accept": "*/*",
                        "Connection": "keep-alive",
                        "User-Agent": "python-requests/2.22.0",
                        "Accept-Encoding": "gzip, deflate",
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
