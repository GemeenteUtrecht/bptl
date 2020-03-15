from django.test import TestCase

from bptl.activiti.models import ServiceTask

from ..models import BRPConfig
from ..tasks import HasDegreeOfKinship

BRP_API_ROOT = "https://haalcentraal.lostlemon.nl/"


class CreateStatusTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        config = BRPConfig.get_solo()
        config.api_root = BRP_API_ROOT
        config.save()

    def test_kinship_1_true(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999993392",
                "burgerservicenummer2": "999990676",
                "kinship": 1,
            },
        )

        task = HasDegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"hasDegreeOfKinship": True})

    def test_kinship_2_spouse_false(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999990421",
                "kinship": 2,
            },
        )

        task = HasDegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"hasDegreeOfKinship": False})

    def test_kinship_2_siblings(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999993392",
                "burgerservicenummer2": "999991978",
                "kinship": 2,
            },
        )

        task = HasDegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"hasDegreeOfKinship": True})

    def test_kinship_2_grandchild(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999991115",
                "kinship": 2,
            },
        )

        task = HasDegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"hasDegreeOfKinship": True})

    def test_kinship_3_uncle(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999991760",
                "burgerservicenummer2": "999991115",
                "kinship": 3,
            },
        )

        task = HasDegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"hasDegreeOfKinship": True})

    def test_kinship_3_son_in_law_false(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999991589",
                "kinship": 3,
            },
        )

        task = HasDegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"hasDegreeOfKinship": False})

    def test_kinship_3_great_grandchildren(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999993392",
                "burgerservicenummer2": "999992612",
                "kinship": 3,
            },
        )

        task = HasDegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"hasDegreeOfKinship": True})

    def test_kinship_4_great_great_grandchildren(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999992612",
                "kinship": 4,
            },
        )

        task = HasDegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"hasDegreeOfKinship": True})
