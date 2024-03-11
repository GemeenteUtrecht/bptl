from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase

import requests_mock
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable
from zgw_consumers.api_models.constants import RolOmschrijving
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.core.models import CoreConfig
from bptl.credentials.tests.factories import AppServiceCredentialsFactory
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory
from bptl.tests.utils import paginated_response
from bptl.work_units.zgw.objects.models import MetaObjectTypesConfig
from bptl.work_units.zgw.objects.tests.utils import (
    START_CAMUNDA_PROCESS_FORM,
    START_CAMUNDA_PROCESS_FORM_OBJ,
)

from ..tasks import StartCamundaProcessTask

ZRC_ROOT = "https://some.zrc.nl/api/v1/"
ZTC_ROOT = "https://some.ztc.nl/api/v1/"
OBJECTS_ROOT = "https://some-objects.nl/api/v1/"
OBJECTTYPES_ROOT = "https://some-objecttypes.nl/api/v1/"
ZAAK_URL = f"{ZRC_ROOT}zaken/some-zaak"
ZAAKTYPE_URL = f"{ZTC_ROOT}zaaktypen/some-zaaktype"
CATALOGUS_URL = f"{ZTC_ROOT}catalogi/some-catalogus"
PROCESS_INSTANCE_ID = "133c2414-1be1-4c24-a520-08f4ebd58d9e"
PROCESS_INSTANCE_URL = (
    f"https://camunda-example.com/engine-rest/process-instance/{PROCESS_INSTANCE_ID}"
)
CAMUNDA_ROOT = "https://some.camunda.com/"
CAMUNDA_API_ROOT = f"{CAMUNDA_ROOT}engine-rest/"


@requests_mock.Mocker()
class StartCamundaProcessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "zaakUrl": serialize_variable(ZAAK_URL),
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
        cls.zrc_service = Service.objects.create(
            label="zrc",
            api_type=APITypes.zrc,
            api_root=ZRC_ROOT,
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
            api_root=ZTC_ROOT,
            auth_type=AuthTypes.no_auth,
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service=cls.ztc_service,
            alias="ztc",
        )
        AppServiceCredentialsFactory.create(
            app__app_id="some-app-id",
            service=cls.zrc_service,
        )
        cls.catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS_URL
        )
        cls.zaaktype = generate_oas_component(
            "ztc", "schemas/ZaakType", url=ZAAKTYPE_URL, catalogus=cls.catalogus["url"]
        )

        cls.zaak = generate_oas_component(
            "zrc", "schemas/Zaak", zaaktype=cls.zaaktype["url"]
        )
        cls.rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=cls.zaak["url"],
            omschrijvingGeneriek=RolOmschrijving.initiator,
            betrokkeneIdentificatie={"identificatie": "user:some-user"},
        )

        camunda_config = CamundaConfig.get_solo()
        camunda_config.root_url = CAMUNDA_ROOT
        camunda_config.rest_api_path = CAMUNDA_API_ROOT
        camunda_config.save()

        objecttypes_service = Service.objects.create(
            label="objecttypes",
            api_type=APITypes.orc,
            api_root=OBJECTTYPES_ROOT,
            auth_type=AuthTypes.no_auth,
        )
        config = CoreConfig.get_solo()
        config.primary_objecttypes_api = objecttypes_service
        config.save()

        metaconfig = MetaObjectTypesConfig.get_solo()
        metaconfig.start_camunda_process_form_objecttype = (
            f"{OBJECTTYPES_ROOT}objecttypes/some-uuid"
        )
        metaconfig.save()

    def test_start_camunda_start_process_success(self, m):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, ZTC_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")

        m.get(ZAAK_URL, json=self.zaak)
        m.get(ZAAKTYPE_URL, json=self.zaaktype)
        m.get(CATALOGUS_URL, json=self.catalogus)
        m.get(
            f"{ZRC_ROOT}rollen?zaak={self.zaak['url']}",
            json={"count": 1, "next": None, "previous": None, "results": [self.rol]},
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )
        with patch(
            "bptl.work_units.zgw.tasks.zaakprocess.start_process",
            return_value={"instance_id": "some-uuid", "instance_url": "some-url"},
        ) as mock_start_process:
            task = StartCamundaProcessTask(self.task)
            response = task.perform()

        mock_start_process.assert_called_once_with(
            process_key=START_CAMUNDA_PROCESS_FORM["camundaProcessDefinitionKey"],
            variables={
                "zaakUrl": serialize_variable(self.zaak["url"]),
                "zaakIdentificatie": serialize_variable(self.zaak["identificatie"]),
                "zaakDetails": serialize_variable(
                    {
                        "omschrijving": self.zaak["omschrijving"],
                        "zaaktypeOmschrijving": self.zaaktype["omschrijving"],
                        "toelichting": self.zaak["toelichting"],
                    }
                ),
                "initiator": serialize_variable("user:some-user"),
                "bptlAppId": serialize_variable("some-app-id"),
            },
        )

    @patch("bptl.work_units.zgw.tasks.zaakprocess.logger")
    def test_start_camunda_start_process_no_form_logger(self, m, mock_logger):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, ZTC_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")

        m.get(ZAAK_URL, json=self.zaak)
        m.get(ZAAKTYPE_URL, json=self.zaaktype)
        m.get(CATALOGUS_URL, json=self.catalogus)
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([]),
        )
        task = StartCamundaProcessTask(self.task)
        response = task.perform()
        self.assertEqual(response, {})
        mock_logger.warning.assert_called_once_with(
            "Did not find a start camunda process form for zaaktype {zt}.".format(
                zt=self.zaaktype["identificatie"]
            )
        )

    def test_start_camunda_start_process_success_initiator_from_camunda(self, m):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, ZTC_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")

        m.get(ZAAK_URL, json=self.zaak)
        m.get(ZAAKTYPE_URL, json=self.zaaktype)
        m.get(CATALOGUS_URL, json=self.catalogus)

        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )
        rol_url = f"{ZRC_ROOT}rollen?zaak={self.zaak['url']}"
        task_dict = deepcopy(self.task_dict)
        task_dict["variables"] = {
            **task_dict["variables"],
            "initiator": serialize_variable("user:some-other-user"),
        }

        task = ExternalTask.objects.create(**task_dict)
        with patch(
            "bptl.work_units.zgw.tasks.zaakprocess.start_process",
            return_value={"instance_id": "some-uuid", "instance_url": "some-url"},
        ) as mock_start_process:
            task = StartCamundaProcessTask(task)
            response = task.perform()

        mock_start_process.assert_called_once_with(
            process_key=START_CAMUNDA_PROCESS_FORM["camundaProcessDefinitionKey"],
            variables={
                "zaakUrl": serialize_variable(self.zaak["url"]),
                "zaakIdentificatie": serialize_variable(self.zaak["identificatie"]),
                "zaakDetails": serialize_variable(
                    {
                        "omschrijving": self.zaak["omschrijving"],
                        "zaaktypeOmschrijving": self.zaaktype["omschrijving"],
                        "toelichting": self.zaak["toelichting"],
                    }
                ),
                "initiator": serialize_variable("user:some-other-user"),
                "bptlAppId": serialize_variable("some-app-id"),
            },
        )

        self.assertNotIn(rol_url, [req.url for req in m.request_history])
