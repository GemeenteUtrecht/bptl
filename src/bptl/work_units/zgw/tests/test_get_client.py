import json

from django.db import IntegrityError
from django.test import TestCase

from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from bptl.camunda.tests.factories import ExternalTaskFactory
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..client import MultipleServices, NoService
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
            api_type=APITypes.zrc,
            api_root=ZRC_URL,
            label="zrc_service",
            slug="zrc-service",
        )

    def test_no_default_services(self):
        self.task.variables = {"bptlAppId": serialize_variable("some-app-id")}
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
            slug="other-zrc-dup",
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
            slug="other-zrc-multi",
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
