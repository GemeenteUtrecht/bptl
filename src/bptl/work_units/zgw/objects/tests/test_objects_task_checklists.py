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
from ..tasks import InitializeChecklistTask
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
class InitializeChecklistTaskTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        config = MetaObjectTypesConfig.get_solo()
        config.checklisttype_objecttype = CHECKLISTTYPE_OBJECTTYPE["url"]
        config.checklist_objecttype = CHECKLIST_OBJECTTYPE["url"]
        config.save()

        cls.task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "zaakUrl": serialize_variable(ZAAK_URL),
                "zaaktypeIdentificatie": serialize_variable(ZAAKTYPE_IDENTIFICATIE),
                "catalogusDomein": serialize_variable("UTRE"),
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
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=OBJECTTYPES_ROOT,
            service__api_type=APITypes.orc,
            service__auth_type=AuthTypes.no_auth,
            alias="objecttypes",
        )

        cls.zrc_service = Service.objects.create(
            label="zrc",
            api_type=APITypes.zrc,
            api_root=ZAKEN_ROOT,
            auth_type=AuthTypes.no_auth,
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service=cls.zrc_service,
            alias="zrc",
        )

        cls.ztc_service = Service.objects.create(
            label="ztc",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
            auth_type=AuthTypes.no_auth,
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service=cls.ztc_service,
            alias="ztc",
        )

        app = AppFactory.create(app_id="some-app-id")
        AppServiceCredentialsFactory.create(
            app=app,
            service=cls.zrc_service,
        )
        AppServiceCredentialsFactory.create(
            app=app,
            service=cls.ztc_service,
        )

    def setUp(self):
        self.mock_parallel_patcher = patch(
            "bptl.work_units.zgw.objects.tasks.parallel",
            return_value=mock_parallel(),
        )
        self.mock_parallel_patcher.start()
        self.addCleanup(self.mock_parallel_patcher.stop)

    def test_missing_variable(self, m):
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
        task = InitializeChecklistTask(task)
        with self.assertRaises(MissingVariable) as exc:
            task.perform()
        self.assertEqual(
            exc.exception.args[0],
            "The variables `catalogusDomein` and `zaaktypeCatalogus` are missing or empty. Please supply either one.",
        )

    def test_missing_checklisttype(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.post(f"{OBJECTS_ROOT}objects/search", json=paginated_response([]))
        task = InitializeChecklistTask(self.task)
        with patch("bptl.work_units.zgw.objects.tasks.logger") as mock_logger:
            response = task.perform()

        mock_logger.warning.assert_called_with(
            f"CHECKLISTTYPE not found for ZAAKTYPE with identificatie: `{ZAAKTYPE_IDENTIFICATIE}` in CATALOGUS with domein: `UTRE`."
        )
        self.assertEqual(response, {"initializedChecklist": False})

    def test_checklist_already_initalized(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS, domein="some-domein"
        )
        m.get(CATALOGUS, json=catalogus)
        task = InitializeChecklistTask(self.task)
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([CHECKLIST_OBJECT]),
        )
        with patch(
            "bptl.work_units.zgw.objects.tasks.fetch_checklisttype",
            return_value=CHECKLISTTYPE_OBJECT,
        ):
            with patch("bptl.work_units.zgw.objects.tasks.logger") as mock_logger:
                response = task.perform()

        mock_logger.warning.assert_called_with("CHECKLIST already exists for ZAAK.")
        self.assertEqual(response, {"initializedChecklist": False})

    def test_initialize_checklist_and_relate_object(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")

        catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS, domein="some-domein"
        )
        m.get(CATALOGUS, json=catalogus)
        m.get(CHECKLIST_OBJECTTYPE["url"], json=CHECKLIST_OBJECTTYPE)
        m.get(
            CHECKLIST_OBJECTTYPE_LATEST_VERSION["url"],
            json=CHECKLIST_OBJECTTYPE_LATEST_VERSION,
        )
        m.post(f"{OBJECTS_ROOT}objects", json=CHECKLIST_OBJECT)

        zaakobject = generate_oas_component(
            "zrc", "schemas/ZaakObject", zaak=ZAAK_URL, object=CHECKLIST_OBJECT["url"]
        )
        m.post(f"{ZAKEN_ROOT}zaakobjecten", json=zaakobject, status_code=201)
        task = InitializeChecklistTask(self.task)
        with patch(
            "bptl.work_units.zgw.objects.tasks.fetch_checklisttype",
            return_value=CHECKLISTTYPE_OBJECT,
        ):
            with patch(
                "bptl.work_units.zgw.objects.tasks.fetch_checklist",
                return_value=[],
            ):
                with patch("bptl.work_units.zgw.objects.tasks.logger") as mock_logger:
                    response = task.perform()

        self.assertEqual(response, {"initializedChecklist": True})
