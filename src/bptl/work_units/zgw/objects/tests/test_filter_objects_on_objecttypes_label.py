from unittest.mock import patch

from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.tasks.base import MissingVariable
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory
from bptl.tests.utils import mock_parallel

from ..models import MetaObjectTypesConfig
from ..tasks import filter_zaakobjects_on_objecttype_label
from .utils import (
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    REVIEW_OBJECT,
    REVIEW_OBJECTTYPE,
    ZAAK_URL,
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
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[])
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
        zaakobjects = filter_zaakobjects_on_objecttype_label(task)
        self.assertEqual(zaakobjects, {"filteredObjects": []})

    def test_objecttypes_empty_label(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=[REVIEW_OBJECTTYPE],
        )
        m.get(f"{REVIEW_OBJECT['url']}", json=REVIEW_OBJECT)
        zaakobject = generate_oas_component(
            "zrc", "schemas/ZaakObject", zaak=ZAAK_URL, object=REVIEW_OBJECT["url"]
        )
        task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "bptlAppId": serialize_variable("some-app-id"),
                "zaakObjects": serialize_variable([zaakobject]),
                "label": serialize_variable(""),
            },
        }
        task = ExternalTask.objects.create(
            **task_dict,
        )
        zaakobjects = filter_zaakobjects_on_objecttype_label(task)
        self.assertEqual(
            zaakobjects,
            {
                "filteredObjects": [
                    {
                        "objectType": REVIEW_OBJECTTYPE["url"],
                        "objectTypeOverige": zaakobject["objectTypeOverige"],
                        "objectUrl": REVIEW_OBJECT["url"],
                        "relatieomschrijving": zaakobject["relatieomschrijving"],
                    }
                ]
            },
        )

    def test_objecttypes_mismatch_label(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=[REVIEW_OBJECTTYPE],
        )
        m.get(f"{REVIEW_OBJECT['url']}", json=REVIEW_OBJECT)
        zaakobject = generate_oas_component(
            "zrc", "schemas/ZaakObject", zaak=ZAAK_URL, object=REVIEW_OBJECT["url"]
        )
        task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "bptlAppId": serialize_variable("some-app-id"),
                "zaakObjects": serialize_variable([zaakobject]),
                "label": serialize_variable("some-label"),
            },
        }
        task = ExternalTask.objects.create(
            **task_dict,
        )
        zaakobjects = filter_zaakobjects_on_objecttype_label(task)
        self.assertEqual(
            zaakobjects,
            {"filteredObjects": []},
        )
