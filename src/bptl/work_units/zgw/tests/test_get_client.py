from django.test import TestCase, override_settings

from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from bptl.camunda.tests.factories import ExternalTaskFactory
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..client import MultipleServices, NoAuth, NoService
from ..tasks import ZGWWorkUnit

ZRC_URL = "https://some.zrc.nl/api/v1/"


class GetZGWClientTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.mapping = TaskMappingFactory.create(topic_name="some-topic")
        cls.task = ExternalTaskFactory.create(topic_name="some-topic")
        cls.work_unit = ZGWWorkUnit(cls.task)
        cls.service = Service.objects.create(
            api_type=APITypes.zrc, api_root=ZRC_URL, label="zrc_service"
        )

    def test_get_client_with_alias(self):
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=self.service, alias="ZRC"
        )
        self.task.variables = {
            "services": {"type": "json", "value": {"ZRC": {"jwt": "Bearer 12345"}}}
        }
        self.task.save()

        client = self.work_unit.get_client(APITypes.zrc)

        self.assertEqual(client.base_url, ZRC_URL)
        self.assertTrue(client.auth_value, "Bearer 12345")

    def test_no_default_services(self):
        self.task.variables = {
            "services": {"type": "json", "value": {"ZRC": {"jwt": "Bearer 12345"}}}
        }
        self.task.save()

        with self.assertRaises(NoService) as exc:
            self.work_unit.get_client(APITypes.zrc)

        self.assertEqual(
            str(exc.exception), "No zrc service is configured for topic some-topic"
        )

    def test_no_alias_in_process_vars(self):
        self.task.variables = {}
        self.task.save()
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=self.service, alias="ZRC"
        )

        with self.assertRaises(NoService) as exc:
            self.work_unit.get_client(APITypes.zrc)

        self.assertEqual(
            str(exc.exception), "Expected service aliases in process variables"
        )

    @override_settings(DEBUG=True)
    def test_no_alias_debug(self):
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=self.service, alias="ZRC"
        )

        client = self.work_unit.get_client(APITypes.zrc)

        self.assertEqual(client.base_url, ZRC_URL)

    def test_no_default_service_with_required_alias(self):
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=self.service, alias="other ZRC"
        )
        self.task.variables = {
            "services": {"type": "json", "value": {"ZRC": {"jwt": "Bearer 12345"}}}
        }
        self.task.save()

        with self.assertRaises(NoService) as exc:
            self.work_unit.get_client(APITypes.zrc)

        self.assertEqual(
            str(exc.exception),
            "No zrc service with aliases ['ZRC'] is configured for topic some-topic",
        )

    def test_two_default_services_with_required_alias(self):
        other_service = Service.objects.create(
            api_type=APITypes.zrc,
            label="other ZRC",
            api_root="https://other.zrc.nl/api/v1/",
        )
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=self.service, alias="ZRC"
        )
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=other_service, alias="ZRC"
        )
        self.task.variables = {
            "services": {"type": "json", "value": {"ZRC": {"jwt": "Bearer 12345"}}}
        }
        self.task.save()

        with self.assertRaises(MultipleServices) as exc:
            self.work_unit.get_client(APITypes.zrc)

        self.assertEqual(
            str(exc.exception),
            "More than one zrc service with aliases ['ZRC'] is configured for topic some-topic",
        )

    def test_no_jwt_in_process_vars(self):
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=self.service, alias="ZRC"
        )
        self.task.variables = {
            "services": {
                "type": "json",
                "value": {"ZRC": {"some_claims": "some value"}},
            }
        }
        self.task.save()

        with self.assertRaises(NoAuth) as exc:
            self.work_unit.get_client(APITypes.zrc)

        self.assertEqual(
            str(exc.exception), "Expected 'jwt' variable for ZRC in process variables"
        )
