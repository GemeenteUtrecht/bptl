from unittest.mock import patch

from django.test import TestCase

from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory
from bptl.tests.utils import paginated_response
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

    @patch("bptl.work_units.zgw.objects.services.MetaObjectTypesConfig")
    def test_wrongly_configured_meta_config(self, mock_meta_config):
        mock_meta_config.start_camunda_process_form_objecttype = ""
        with patch(
            "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig.get_solo",
            return_value=mock_meta_config,
        ):
            with self.assertRaises(RuntimeError):
                fetch_start_camunda_process_form(
                    self.task, zaaktype_identificatie="", catalogus_domein=""
                )

    @patch("bptl.work_units.zgw.objects.services.MetaObjectTypesConfig")
    def test_no_zaaktype_provided(self, mock_meta_config):
        mock_meta_config.start_camunda_process_form_objecttype = (
            START_CAMUNDA_PROCESS_FORM_OT["url"]
        )
        with patch(
            "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig.get_solo",
            return_value=mock_meta_config,
        ):
            with patch("bptl.work_units.zgw.objects.services.logger") as mock_logger:
                fetch_start_camunda_process_form(
                    self.task, zaaktype_identificatie="", catalogus_domein="val"
                )
        mock_logger.warning.assert_called_once_with(
            "If ZAAK is not provided - zaaktype_identificatie and catalogus_domein MUST be provided."
        )

    @patch(
        "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
    )
    def test_no_catalogus_provided(self, mock_meta_config):
        mock_meta_config.start_camunda_process_form_objecttype = (
            START_CAMUNDA_PROCESS_FORM_OT["url"]
        )
        with patch(
            "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig.get_solo",
            return_value=mock_meta_config,
        ):
            with patch("bptl.work_units.zgw.objects.services.logger") as mock_logger:
                fetch_start_camunda_process_form(
                    self.task, zaaktype_identificatie="val", catalogus_domein=""
                )
        mock_logger.warning.assert_called_once_with(
            "If ZAAK is not provided - zaaktype_identificatie and catalogus_domein MUST be provided."
        )

    @patch(
        "bptl.work_units.zgw.objects.services.search_objects",
        return_value=[paginated_response([]), {}],
    )
    @patch("bptl.work_units.zgw.objects.services.logger")
    @patch("bptl.work_units.zgw.objects.services.MetaObjectTypesConfig")
    def test_no_objects_found(self, mock_meta_config, mock_logger, mock_search_objects):
        fetch_start_camunda_process_form(
            self.task, zaaktype_identificatie="some-id", catalogus_domein="some-domein"
        )
        mock_logger.warning.assert_called_once()

    @patch(
        "bptl.work_units.zgw.objects.services.search_objects",
        return_value=[paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ, 2]), {}],
    )
    @patch("bptl.work_units.zgw.objects.services.logger")
    @patch(
        "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
    )
    def test_more_than_one_objects_found(
        self, mock_meta_config, mock_logger, mock_search_objects
    ):
        fetch_start_camunda_process_form(
            self.task, zaaktype_identificatie="zaaktype", catalogus_domein="catalogus"
        )
        mock_logger.warning.assert_called_once()

    @patch(
        "bptl.work_units.zgw.objects.services.search_objects",
        return_value=[paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]), {}],
    )
    @patch("bptl.work_units.zgw.objects.services.logger")
    @patch(
        "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
    )
    def test_success(self, mock_meta, mock_logger, mock_search_objects):
        with patch(
            "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
            side_effect=Exception,
        ):
            fetch_start_camunda_process_form(
                self.task,
                zaaktype_identificatie="zaaktype",
                catalogus_domein="catalogus",
            )

        mock_search_objects.assert_called_once()
        mock_logger.warning.assert_not_called()
