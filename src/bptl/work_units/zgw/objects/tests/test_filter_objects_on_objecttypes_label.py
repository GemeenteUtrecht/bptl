from unittest.mock import patch

from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.credentials.tests.factories import AppFactory, AppServiceCredentialsFactory
from bptl.tasks.base import MissingVariable
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory
from bptl.tests.utils import mock_parallel, paginated_response

from ..models import MetaObjectTypesConfig
from ..tasks import filter_zaakobjects_on_objecttype_label
from .utils import (
    CATALOGI_ROOT,
    CATALOGUS,
    CHECKLIST_OBJECT,
    CHECKLIST_OBJECTTYPE,
    CHECKLIST_OBJECTTYPE_LATEST_VERSION,
    CHECKLISTTYPE_OBJECT,
    CHECKLISTTYPE_OBJECTTYPE,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
)

ZAAKTYPE_IDENTIFICATIE = "ZAAKTYPE-2023-12345567"


@requests_mock.Mocker()
class FilterObjectsTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        config = MetaObjectTypesConfig.get_solo()
        config.checklisttype_objecttype = "https://some-objecttypes-url.com/1234"
        config.save()

        mapping = TaskMappingFactory.create(topic_name="some-topic-name")
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=OBJECTS_ROOT,
            service__api_type=APITypes.orc,
            service__auth_type=AuthTypes.no_auth,
            alias="objects",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=OBJECTTYPES_ROOT,
            service__api_type=APITypes.orc,
            service__auth_type=AuthTypes.no_auth,
            alias="objecttypes",
        )

        cls.mock_parallel_patcher = patch(
            "bptl.work_units.zgw.objects.tasks.parallel",
            return_value=mock_parallel(),
        )

    def setUp(self):
        self.mock_parallel_patcher.start()
        self.addCleanup(self.mock_parallel_patcher.stop)

    def test_missing_zaakobjects_variable(self, m):
        task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "bptlAppId": serialize_variable("some-app-id"),
            },
        }
        task = ExternalTask.objects.create(
            **task_dict,
        )

        with self.assertRaises(MissingVariable) as exc:
            filter_zaakobjects_on_objecttype_label(task)

        self.assertEqual(
            exc.exception.args[0], "The variable zaakObjects is missing or empty."
        )

    def test_empty_zaakobjects_variable(self, m):
        task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "bptlAppId": serialize_variable("some-app-id"),
                "zaakObjects": serialize_variable([]),
            },
        }
        task = ExternalTask.objects.create(
            **task_dict,
        )

        zaakobjects = filter_zaakobjects_on_objecttype_label(task)

        self.assertEqual(zaakobjects, {"filteredObjects": []})

    def test_missing_label_variable(self, m):
        task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "bptlAppId": serialize_variable("some-app-id"),
                "zaakObjects": serialize_variable(["some-object"]),
            },
        }
        task = ExternalTask.objects.create(
            **task_dict,
        )

        with self.assertRaises(MissingVariable) as exc:
            filter_zaakobjects_on_objecttype_label(task)

        self.assertEqual(
            exc.exception.args[0], "The variable label is missing or empty."
        )

    def test_no_objecttypes(self, m):
        task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "bptlAppId": serialize_variable("some-app-id"),
                "zaakObjects": serialize_variable(["some-object"]),
                "label": serialize_variable("some-label"),
            },
        }
        task = ExternalTask.objects.create(
            **task_dict,
        )
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=paginated_response([]))
        zaakobjects = filter_zaakobjects_on_objecttype_label(task)
        self.assertEqual(zaakobjects, {"filteredObjects": []})
