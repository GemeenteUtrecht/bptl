from unittest.mock import MagicMock, patch

from django.test import TestCase

from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory
from bptl.work_units.zgw.objects.services import fetch_start_camunda_process_form
from bptl.work_units.zgw.objects.tests.utils import (
    START_CAMUNDA_PROCESS_FORM_OBJ,
    START_CAMUNDA_PROCESS_FORM_OT,
)

OBJECTS_ROOT = "https://some-objects.nl/api/v1/"


class ObjectsServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "bptlAppId": serialize_variable("some-app-id"),
            },
        }
        cls.task = ExternalTask.objects.create(
            **cls.task_dict,
        )
        mapping = TaskMappingFactory.create(topic_name="some-topic-name")
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=OBJECTS_ROOT,
            service__api_type=APITypes.orc,
            service__auth_type=AuthTypes.no_auth,
            alias="objects",
        )

    @patch(
        "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
    )
    def test_wrongly_configured_meta_config(self, mock_meta_config):
        with self.assertRaises(RuntimeError):
            fetch_start_camunda_process_form(self.task, zaaktype={}, catalogus={})

    @patch(
        "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
    )
    def test_no_zaaktype_provided(self, mock_meta_config):
        with self.assertRaises(RuntimeError):
            fetch_start_camunda_process_form(
                self.task, zaaktype={"key": "val"}, catalogus={}
            )

    @patch(
        "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
    )
    def test_no_catalogus_provided(self, mock_meta_config):
        config = MagicMock()
        config.ot_url = START_CAMUNDA_PROCESS_FORM_OT["url"]
        mock_meta_config.get_solo = config
        with self.assertRaises(RuntimeError):
            fetch_start_camunda_process_form(
                self.task, zaaktype={}, catalogus={"key": "val"}
            )

    @patch("bptl.work_units.zgw.objects.services.search_objects", return_value=[])
    @patch("bptl.work_units.zgw.objects.services.logger")
    @patch("bptl.work_units.zgw.objects.services.MetaObjectTypesConfig")
    def test_no_objects_found(self, mock_meta_config, mock_logger, mock_search_objects):
        zaaktype = {"identificatie": "some-id"}
        catalogus = {"domein": "some-domein"}
        fetch_start_camunda_process_form(
            self.task, zaaktype=zaaktype, catalogus=catalogus
        )
        mock_logger.warning.assert_called_once()

    @patch(
        "bptl.work_units.zgw.objects.services.search_objects",
        return_value=[START_CAMUNDA_PROCESS_FORM_OBJ, 2],
    )
    @patch("bptl.work_units.zgw.objects.services.logger")
    @patch(
        "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
    )
    def test_more_than_one_objects_found(
        self, mock_meta_config, mock_logger, mock_search_objects
    ):
        zaaktype = {"identificatie": "some-id"}
        catalogus = {"domein": "some-domein"}
        fetch_start_camunda_process_form(
            self.task, zaaktype=zaaktype, catalogus=catalogus
        )
        mock_logger.warning.assert_called_once()

    @patch(
        "bptl.work_units.zgw.objects.services.search_objects",
        return_value=[START_CAMUNDA_PROCESS_FORM_OBJ],
    )
    @patch("bptl.work_units.zgw.objects.services.logger")
    @patch(
        "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
    )
    def test_success(self, mock_meta, mock_logger, mock_search_objects):
        zaaktype = {"identificatie": "some-id"}
        catalogus = {"domein": "some-domein"}
        with patch(
            "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
            side_effect=Exception,
        ):
            fetch_start_camunda_process_form(
                self.task, zaaktype=zaaktype, catalogus=catalogus
            )

        mock_search_objects.assert_called_once()
        mock_logger.warning.assert_not_called()
