import json

from django.test import TestCase

import requests_mock

from bptl.activiti.models import ServiceTask

from ..tasks import BRP_API_ROOT, IsAboveAge

PERSON_URL = f"{BRP_API_ROOT}ingeschrevenpersonen/999999011?fields=leeftijd"


@requests_mock.Mocker()
class CreateStatusTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={"burgerservicenummer": "999999011", "age": 18,},
        )

    def test_above_age(self, m):
        m.get(
            PERSON_URL, json={"leeftijd": 36, "_links": {"self": {"href": PERSON_URL}}}
        )
        task = IsAboveAge(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"isAboveAge": True})

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
