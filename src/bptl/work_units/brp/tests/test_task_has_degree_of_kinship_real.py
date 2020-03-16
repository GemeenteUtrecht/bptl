from django.test import TestCase

from bptl.activiti.models import ServiceTask

from ..models import BRPConfig
from ..tasks import DegreeOfKinship

BRP_API_ROOT = "https://haalcentraal.lostlemon.nl/"


class DegreeOfKinshipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        config = BRPConfig.get_solo()
        config.api_root = BRP_API_ROOT
        config.save()

    def test_children_1(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999993392",
                "burgerservicenummer2": "999990676",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 1})

    def test_spouse_none(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999990421",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": None})

    def test_siblings_2(self):
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

    def test_grandchild_2(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999991115",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 2})

    def test_uncle_3(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999991760",
                "burgerservicenummer2": "999991115",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 3})

    def test_son_in_law_none(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999991589",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": None})

    def test_great_grandchildren_3(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999993392",
                "burgerservicenummer2": "999992612",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 3})

    def test_great_great_grandchildren_4(self):
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

    # todo
    def test_cousins_4(self):
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

    def test_great_uncle_4(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999991115",
                "burgerservicenummer2": "999992612",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": 4})

    def test_grand_parents_in_law_none(self):
        # parents of son-n-law
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

    def test_grand_son_in_law_none(self):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": "999990676",
                "burgerservicenummer2": "999994347",
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": None})
