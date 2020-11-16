from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.activiti.models import ServiceTask
from bptl.credentials.tests.factories import AppServiceCredentialsFactory
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory

from ..tasks import IsAboveAge

BRP_API_ROOT = "http://brp.example.com/"
PERSON_URL = f"{BRP_API_ROOT}ingeschrevenpersonen/999999011?fields=leeftijd"


@requests_mock.Mocker()
class IsAboveAgeTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "bptlAppId": "some-app-id",
                "burgerservicenummer": "999999011",
                "age": 18,
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

    def test_above_age_service_credentials(self, m):
        del self.fetched_task.variables["bptlAppId"]
        self.fetched_task.save()
        m.get(
            PERSON_URL, json={"leeftijd": 36, "_links": {"self": {"href": PERSON_URL}}}
        )
        task = IsAboveAge(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"isAboveAge": True})

        # check auth
        self.assertEqual(m.last_request.headers["X-Api-Key"], "12345")

    def test_above_age(self, m):
        m.get(
            PERSON_URL, json={"leeftijd": 36, "_links": {"self": {"href": PERSON_URL}}}
        )
        task = IsAboveAge(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"isAboveAge": True})

        # check auth
        self.assertEqual(m.last_request.headers["Other-Header"], "foobarbaz")

    def test_equal_age(self, m):
        m.get(
            PERSON_URL, json={"leeftijd": 18, "_links": {"self": {"href": PERSON_URL}}}
        )
        task = IsAboveAge(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"isAboveAge": True})

    def test_below_age(self, m):
        m.get(
            PERSON_URL, json={"leeftijd": 17, "_links": {"self": {"href": PERSON_URL}}}
        )
        task = IsAboveAge(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"isAboveAge": False})

    def test_none_age(self, m):
        m.get(PERSON_URL, json={"_links": {"self": {"href": PERSON_URL}}})
        task = IsAboveAge(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"isAboveAge": None})
