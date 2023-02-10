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


@patch("bptl.work_units.zgw.objects.services.MetaObjectTypesConfig")
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
        cls.task_url = ExternalTask.objects.create(
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
            omschrijving_generiek=RolOmschrijving.initiator,
            betrokkene_identificatie={"identificatie": "user:some-user"},
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

    def test_start_camunda_start_process_success(self, mock_meta, m):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, ZTC_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")

        m.get(ZAAK_URL, json=self.zaak)
        m.get(ZAAKTYPE_URL, json=self.zaaktype)
        m.get(CATALOGUS_URL, json=self.catalogus)
        m.get(f"{ZRC_ROOT}rollen?zaak={self.zaak['url']}", json=[self.rol])
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=[START_CAMUNDA_PROCESS_FORM_OBJ],
        )
        with patch(
            "bptl.work_units.zgw.tasks.zaakprocess.start_process",
            return_value={"instance_id": "some-uuid", "instance_url": "some-url"},
        ) as mock_start_process:
            task = StartCamundaProcessTask(self.task_url)
            response = task.perform()

        mock_start_process.assert_called_once_with(
            process_key=START_CAMUNDA_PROCESS_FORM["camundaProcessDefinitionKey"],
            variables={
                "zaakUrl": self.zaak["url"],
                "zaakIdentificatie": self.zaak["identificatie"],
                "zaakDetails": {
                    "omschrijving": self.zaak["omschrijving"],
                    "zaaktypeOmschrijving": self.zaaktype["omschrijving"],
                },
            },
        )