from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory
from bptl.tests.utils import paginated_response
from bptl.work_units.zgw.tests.compat import (
    generate_oas_component,
    mock_service_oas_get,
)

from ..objects.tests.utils import OBJECTS_ROOT
from ..tasks import FetchZaakObjects

ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"


@requests_mock.Mocker()
class FetchZaakObjectsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMappingFactory.create(topic_name="some-topic")
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=ZRC_URL,
            service__api_type="zrc",
            alias="ZRC",
        )
        cls.zaakobject = generate_oas_component(
            "zrc",
            "schemas/ZaakObject",
            url=f"{ZRC_URL}zaakobjecten/f79989d3-9ac4-4c2b-a94e-13191b333444",
            zaak=ZAAK,
            object=f"{OBJECTS_ROOT}objecten/d859f08e-6957-44f8-9efb-502d18c28f8f",
            object_identificatie=dict(),
        )

    def test_fetch_zaakobjects(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            f"{ZRC_URL}zaakobjecten?zaak={ZAAK}",
            json=paginated_response([self.zaakobject]),
        )
        fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "hoofdZaakUrl": serialize_variable(ZAAK),
                "bptlAppId": serialize_variable({"ZRC": {"jwt": "Bearer 12345"}}),
            },
        )
        task = FetchZaakObjects(fetched_task)

        result = task.perform()
        self.assertEqual(
            result,
            {"zaakObjects": [self.zaakobject]},
        )

    def test_fetch_zaakobjects_no_hoofdzaakurl(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            f"{ZRC_URL}zaakobjecten?zaak={ZAAK}",
            json=paginated_response([self.zaakobject]),
        )
        fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={"bptlAppId": serialize_variable("some-app-id")},
        )
        task = FetchZaakObjects(fetched_task)

        result = task.perform()
        self.assertEqual(result, None)
