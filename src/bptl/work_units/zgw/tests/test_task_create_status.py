from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from freezegun import freeze_time

from bptl.camunda.models import ExternalTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory

from ..tasks import CreateStatusTask
from .utils import mock_service_oas_get

ZTC_URL = "https://some.ztc.nl/api/v1/"
ZRC_URL = "https://some.zrc.nl/api/v1/"
ZAAKTYPE = f"{ZTC_URL}zaaktypen/b241e48e-0f92-4e4f-84b2-01427c027e91"
STATUSTYPE = f"{ZTC_URL}statustypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
STATUS = f"{ZRC_URL}statussen/b7218c76-7478-41e9-a088-54d2f914a713"


@requests_mock.Mocker(real_http=True)
class CreateStatusTaskTests(TestCase):
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
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=ZTC_URL,
            service__api_type="ztc",
            alias="ZTC",
        )
        cls.fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaakUrl": serialize_variable(ZAAK),
                "statustype": serialize_variable(STATUSTYPE),
                "services": serialize_variable({"ZRC": {"jwt": "Bearer 12345"}}),
                "toelichting": serialize_variable("some description"),
            },
        )

    @freeze_time("2020-01-16")
    def test_create_status(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.post(
            f"{ZRC_URL}statussen",
            status_code=201,
            json={
                "url": STATUS,
                "uuid": "b7218c76-7478-41e9-a088-54d2f914a713",
                "zaak": ZAAK,
                "statustype": STATUSTYPE,
                "datumStatusGezet": "2020-01-16T00:00:00+00:00",
                "statustoelichting": "some description",
            },
        )

        task = CreateStatusTask(self.fetched_task)

        result = task.perform()

        self.assertEqual(result, {"statusUrl": STATUS})
        self.assertEqual(
            m.last_request.json(),
            {
                "zaak": ZAAK,
                "statustype": STATUSTYPE,
                "datumStatusGezet": "2020-01-16T00:00:00+00:00",
                "statustoelichting": "some description",
            },
        )

    @freeze_time("2020-01-16")
    def test_create_status_volgnummer(self, m):
        mock_service_oas_get(m, ZRC_URL, "zrc")
        mock_service_oas_get(m, ZTC_URL, "ztc")

        task = ExternalTask.objects.create(
            topic_name="some-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaakUrl": serialize_variable(ZAAK),
                "statusVolgnummer": serialize_variable(2),
                "services": serialize_variable(
                    {
                        "ZRC": {"jwt": "Bearer 12345"},
                        "ZTC": {"jwt": "Bearer 12345"},
                    }
                ),
                "toelichting": serialize_variable("some description"),
            },
        )

        m.get(ZAAK, json={"url": ZAAK, "zaaktype": ZAAKTYPE})
        m.get(
            f"{ZTC_URL}statustypen?zaaktype={ZAAKTYPE}",
            json={
                "count": 2,
                "previous": None,
                "next": None,
                "results": [
                    {
                        "url": "https://example.com",
                        "zaaktype": ZAAKTYPE,
                        "volgnummer": 1,
                        # rest is not relevant
                    },
                    {
                        "url": STATUSTYPE,
                        "zaaktype": ZAAKTYPE,
                        "volgnummer": 2,
                    },
                ],
            },
        )

        m.post(
            f"{ZRC_URL}statussen",
            status_code=201,
            json={
                "url": STATUS,
                "uuid": "b7218c76-7478-41e9-a088-54d2f914a713",
                "zaak": ZAAK,
                "statustype": STATUSTYPE,
                "datumStatusGezet": "2020-01-16T00:00:00+00:00",
                "statustoelichting": "some description",
            },
        )

        work_unit = CreateStatusTask(task)

        result = work_unit.perform()

        self.assertEqual(result, {"statusUrl": STATUS})
        self.assertEqual(
            m.last_request.json(),
            {
                "zaak": ZAAK,
                "statustype": STATUSTYPE,
                "datumStatusGezet": "2020-01-16T00:00:00+00:00",
                "statustoelichting": "some description",
            },
        )
