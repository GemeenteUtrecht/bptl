from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse_lazy

from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from bptl.accounts.models import User

from ..models import DefaultService, TaskMapping
from ..registry import WorkUnitRegistry

# Set up an isolated registry for tests
test_register = WorkUnitRegistry()


@test_register
def task1(task):
    """Task 1 documentation"""
    pass


@override_settings(
    AUTHENTICATION_BACKENDS=[
        "bptl.accounts.backends.UserModelEmailBackend",
        "django.contrib.auth.backends.ModelBackend",
    ]
)
class AddDefaultServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("super", "user@utrecht.nl", "letmein")

    def setUp(self):
        self.client.login(username="super", password="letmein")

        patcher = patch("bptl.tasks.forms.register", new=test_register)
        self.mocked_register = patcher.start()
        self.addCleanup(patcher.stop)

        self.url = reverse_lazy("tasks:taskmapping-create")

        self.data = {
            "topic_name": "foo",
            "callback": "bptl.tasks.tests.test_add_defaultservices.task1",
            "defaultservice_set-TOTAL_FORMS": 2,
            "defaultservice_set-INITIAL_FORMS": 0,
            "defaultservice_set-MIN_NUM_FORMS": 0,
            "defaultservice_set-MAX_NUM_FORMS": 1000,
            "defaultservice_set-0-alias": "",
            "defaultservice_set-0-service": "",
            "defaultservice_set-1-alias": "",
            "defaultservice_set-1-service": "",
        }

    def tearDown(self) -> None:
        super().tearDown()
        self.client.logout()

    def test_add_one_defaulservice(self):
        zrc = Service.objects.create(
            api_type=APITypes.zrc,
            label="ZRC",
            api_root="https://other.zrc.nl/api/v1/",
            slug="zrc-one-default",
        )

        data = self.data.copy()
        data["defaultservice_set-0-alias"] = "foo zrc"
        data["defaultservice_set-0-service"] = zrc.id

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(TaskMapping.objects.count(), 1)

        task_mapping = TaskMapping.objects.get()
        self.assertEqual(task_mapping.defaultservice_set.count(), 1)

        defaultservice = task_mapping.defaultservice_set.get()
        self.assertEqual(defaultservice.service, zrc)
        self.assertEqual(defaultservice.alias, "foo zrc")

    def test_add_two_defaultservices(self):
        zrc = Service.objects.create(
            api_type=APITypes.zrc,
            label="ZRC",
            api_root="https://some.zrc.nl/api/v1/",
            slug="zrc-two-defaults",
        )
        ztc = Service.objects.create(
            api_type=APITypes.ztc,
            label="ZTC",
            api_root="https://some.ztc.nl/api/v1/",
            slug="ztc-two-defaults",
        )

        data = self.data.copy()
        data["defaultservice_set-0-alias"] = "foo zrc"
        data["defaultservice_set-0-service"] = zrc.id
        data["defaultservice_set-1-alias"] = "foo ztc"
        data["defaultservice_set-1-service"] = ztc.id

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(TaskMapping.objects.count(), 1)

        task_mapping = TaskMapping.objects.get()
        self.assertEqual(task_mapping.defaultservice_set.count(), 2)

        defaultservice1, defaultservice2 = task_mapping.defaultservice_set.order_by(
            "alias"
        ).all()
        self.assertEqual(defaultservice1.service, zrc)
        self.assertEqual(defaultservice1.alias, "foo zrc")
        self.assertEqual(defaultservice2.service, ztc)
        self.assertEqual(defaultservice2.alias, "foo ztc")

    def test_add_zero_defaultservices(self):
        data = self.data.copy()

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(TaskMapping.objects.count(), 1)

        task_mapping = TaskMapping.objects.get()

        self.assertEqual(task_mapping.defaultservice_set.count(), 0)
        self.assertEqual(DefaultService.objects.count(), 0)

    def test_add_two_same_services_fail(self):
        zrc = Service.objects.create(
            api_type=APITypes.zrc,
            label="ZRC",
            api_root="https://some.zrc.nl/api/v1/",
            slug="zrc-same-services-fail",
        )

        data = self.data.copy()
        data["defaultservice_set-0-alias"] = "foo zrc"
        data["defaultservice_set-0-service"] = zrc.id
        data["defaultservice_set-1-alias"] = "same zrc"
        data["defaultservice_set-1-service"] = zrc.id

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TaskMapping.objects.count(), 0)
        self.assertEqual(DefaultService.objects.count(), 0)
