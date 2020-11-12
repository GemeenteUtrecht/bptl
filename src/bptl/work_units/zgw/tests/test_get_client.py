import json

from django.db import IntegrityError
from django.test import TestCase

from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from bptl.camunda.tests.factories import ExternalTaskFactory
from bptl.tasks.tests.factories import TaskMappingFactory
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory

from ..client import MultipleServices, NoAuth, NoService
from ..tasks.base import ZGWWorkUnit

ZRC_URL = "https://some.zrc.nl/api/v1/"


class GetZGWClientTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.mapping = TaskMappingFactory.create(topic_name="some-topic")
        cls.task = ExternalTaskFactory.create(topic_name="some-topic")
        cls.work_unit = ZGWWorkUnit(cls.task)
        cls.service = Service.objects.create(
            api_type=APITypes.zrc, api_root=ZRC_URL, label="zrc_service"
        )

    def test_get_client_with_alias(self):
        # The pre-1.0 behaviour. This is deprecated.
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=self.service, alias="ZRC"
        )
        self.task.variables = {
            "services": {
                "type": "json",
                "value": json.dumps({"ZRC": {"jwt": "Bearer 12345"}}),
            }
        }
        self.task.save()

        with self.assertWarns(DeprecationWarning):
            client = self.work_unit.get_client(APITypes.zrc)

        self.assertEqual(client.base_url, ZRC_URL)
        self.assertTrue(client.auth_value, "Bearer 12345")

    def test_no_default_services(self):
        variant_variables = {
            "old": {"services": serialize_variable({"ZRC": {"jwt": "Bearer 12345"}})},
            "new": {"bptlAppId": serialize_variable("some-app-id")},
        }

        for variant, variables in variant_variables.items():
            with self.subTest(variant=variant):
                self.task.variables = variables
                self.task.save()

                with self.assertRaises(NoService) as exc:
                    self.work_unit.get_client(APITypes.zrc)

                self.assertEqual(
                    str(exc.exception),
                    "No zrc service is configured for topic 'some-topic'",
                )

    def test_no_alias_in_process_vars(self):
        self.task.variables = {}
        self.task.save()
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=self.service, alias="ZRC"
        )

        with self.assertRaisesMessage(
            NoService, "Could not determine service credentials."
        ):
            self.work_unit.get_client(APITypes.zrc)

    def test_duplicated_alias(self):
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=self.service, alias="ZRC"
        )
        other_service = Service.objects.create(
            api_type=APITypes.zrc,
            label="other ZRC",
            api_root="https://other.zrc.nl/api/v1/",
        )
        with self.assertRaises(IntegrityError):
            DefaultServiceFactory.create(
                task_mapping=self.mapping, service=other_service, alias="ZRC"
            )

    def test_multiple_services_same_type(self):
        other_service = Service.objects.create(
            api_type=APITypes.zrc,
            label="other ZRC",
            api_root="https://other.zrc.nl/api/v1/",
        )
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=self.service, alias="ZRC1"
        )
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=other_service, alias="ZRC2"
        )

        err_message = "Multiple 'zrc' services configured for topic 'some-topic'"
        with self.assertRaisesMessage(MultipleServices, err_message):
            self.work_unit.get_client(APITypes.zrc)

    def test_no_jwt_in_process_vars(self):
        # Deprecated
        DefaultServiceFactory.create(
            task_mapping=self.mapping, service=self.service, alias="ZRC"
        )
        self.task.variables = {
            "services": serialize_variable({"ZRC": {"some_claims": "some value"}})
        }
        self.task.save()

        err_message = "Expected 'jwt' key for service with alias 'ZRC'"
        with self.assertWarns(DeprecationWarning):
            with self.assertRaisesMessage(NoAuth, err_message):
                self.work_unit.get_client(APITypes.zrc)
