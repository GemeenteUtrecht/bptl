from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.activiti.models import ServiceTask
from bptl.tasks.tests.factories import DefaultServiceFactory

from ..tasks import DegreeOfKinship
from .utils import NAMES, mock_family

BRP_API_ROOT = "http://brp.example.com/"


@requests_mock.Mocker()
class DegreeOfKinshipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        brp = Service.objects.create(
            api_root=BRP_API_ROOT,
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
        )
        DefaultServiceFactory.create(
            task_mapping__topic_name="some-topic",
            service=brp,
            alias="brp",
        )

    def test_same_bsn(self, m):
        fetched_task = ServiceTask.objects.create(
            topic_name="some-topic",
            variables={
                "burgerservicenummer1": NAMES["JANE"],
                "burgerservicenummer2": NAMES["JANE"],
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
                "burgerservicenummer1": NAMES["JANE"],
                "burgerservicenummer2": NAMES["JILL"],
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
                "burgerservicenummer1": NAMES["LISA"],
                "burgerservicenummer2": NAMES["JACK"],
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
                "burgerservicenummer1": NAMES["JILL"],
                "burgerservicenummer2": NAMES["RICK"],
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
                "burgerservicenummer1": NAMES["JANE"],
                "burgerservicenummer2": NAMES["MARY"],
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
                "burgerservicenummer1": NAMES["RICK"],
                "burgerservicenummer2": NAMES["MARY"],
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
                "burgerservicenummer1": NAMES["MARY"],
                "burgerservicenummer2": NAMES["JACK"],
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
                "burgerservicenummer1": NAMES["JANE"],
                "burgerservicenummer2": NAMES["LISA"],
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
                "burgerservicenummer1": NAMES["JANE"],
                "burgerservicenummer2": NAMES["BART"],
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
                "burgerservicenummer1": NAMES["JOHN"],
                "burgerservicenummer2": NAMES["MARY"],
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
                "burgerservicenummer1": NAMES["RICK"],
                "burgerservicenummer2": NAMES["LISA"],
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
                "burgerservicenummer1": NAMES["MARY"],
                "burgerservicenummer2": NAMES["KATE"],
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
                "burgerservicenummer1": NAMES["JACK"],
                "burgerservicenummer2": NAMES["JILL"],
            },
        )

        task = DegreeOfKinship(fetched_task)

        result = task.perform()

        self.assertEqual(result, {"kinship": None})
