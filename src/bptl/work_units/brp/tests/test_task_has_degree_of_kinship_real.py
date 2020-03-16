from django.test import TestCase

import requests_mock

from bptl.activiti.models import ServiceTask

from ..models import BRPConfig
from ..tasks import DegreeOfKinship
from .utils import mock_family

BRP_API_ROOT = "http://brp.example.com/"


@requests_mock.Mocker()
class DegreeOfKinshipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        config = BRPConfig.get_solo()
        config.api_root = BRP_API_ROOT
        config.save()

    def test_same_bsn(self, m):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999990676",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": None})

    def test_children_1(self, m):
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999993392",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 1})

    def test_spouse_none(self, m):
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999994177",
                "burgerservicenummer2": "999995224",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": None})

    def test_siblings_2(self, m):
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999993392",
                "burgerservicenummer2": "999991978",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 2})

    def test_grandchild_2(self, m):
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999992223",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 2})

    def test_uncle_3(self, m):
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999991978",
                "burgerservicenummer2": "999992223",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 3})

    def test_son_in_law_none(self, m):
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999992223",
                "burgerservicenummer2": "999995224",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": None})

    def test_great_grandchildren_3(self, m):
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999994177",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 3})

    def test_great_great_grandchildren_4(self, m):
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999992612",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 4})

    def test_cousins_4(self, m):
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999993333",
                "burgerservicenummer2": "999992223",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 4})

    def test_great_uncle_4(self, m):
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999991978",
                "burgerservicenummer2": "999994177",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 4})

    def test_grand_parents_in_law_none(self, m):
        # parents of son-n-law
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999992223",
                "burgerservicenummer2": "999991929",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": None})

    def test_grand_son_in_law_none(self, m):
        mock_family(m, BRP_API_ROOT)
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999995224",
                "burgerservicenummer2": "999993392",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": None})
