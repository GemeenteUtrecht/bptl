from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

import requests_mock
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable
from freezegun import freeze_time

from bptl.camunda.tests.factories import ExternalTaskFactory
from bptl.tasks.api import TaskExpired
from bptl.tasks.models import TaskMapping
from bptl.tasks.tests.factories import DefaultServiceFactory
from bptl.utils.constants import Statuses
from bptl.utils.decorators import save_and_log
from bptl.work_units.zgw.tests.compat import mock_service_oas_get

from ..tasks import task_execute_and_complete, task_fetch_and_lock


class RouteTaskTests(TestCase):
    @patch("bptl.camunda.tasks.task_execute_and_complete.delay")
    def test_task_fetch_and_lock(self, m_test_execute):
        task1, task2 = ExternalTaskFactory.create_batch(2, worker_id="aWorkerId")

        with patch(
            "bptl.camunda.tasks.fetch_and_lock",
            return_value=("aWorkerId", 2, [task1, task2]),
        ):

            result = task_fetch_and_lock()

        self.assertEqual(result, 2)

        self.assertEqual(m_test_execute.call_count, 2)
        m_test_execute.assert_any_call(task1.id)
        m_test_execute.assert_any_call(task2.id)

    @patch("bptl.camunda.tasks.complete")
    @patch("bptl.camunda.tasks.execute")
    def test_task_execute_and_complete_success(self, m_execute, m_complete):
        task = ExternalTaskFactory.create()

        task_execute_and_complete(task.id)

        m_execute.assert_called_once()
        m_complete.assert_called_once_with(task)

    @patch("bptl.camunda.tasks.fail_task")
    @patch("bptl.camunda.tasks.complete")
    @patch("bptl.camunda.tasks.execute", side_effect=Exception("execution is failed"))
    def test_task_execute_and_complete_fail_execute(
        self, m_execute, m_complete, m_fail_task
    ):
        @save_and_log()
        def new_execute(task, registry):
            raise Exception("execution is failed")

        m_execute.side_effect = new_execute

        task = ExternalTaskFactory.create()

        task_execute_and_complete(task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, "failed")
        self.assertTrue(task.execution_error.strip().endswith("execution is failed"))

        m_execute.assert_called_once()
        m_complete.assert_not_called()
        m_fail_task.assert_called_once_with(task)

    @patch("bptl.camunda.tasks.complete", side_effect=Exception("completion failed"))
    @patch("bptl.camunda.tasks.execute")
    def test_task_execute_and_complete_fail_complete(self, m_execute, m_complete):
        @save_and_log()
        def new_complete(task):
            raise Exception("completion failed")

        m_complete.side_effect = new_complete
        task = ExternalTaskFactory.create()

        task_execute_and_complete(task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, "failed")
        self.assertTrue(task.execution_error.strip().endswith("completion failed"))

        m_execute.assert_called_once()
        m_complete.assert_called_once_with(task)

    @patch("bptl.camunda.tasks.logger.warning")
    def test_task_execute_already_run(self, m_logger):
        task = ExternalTaskFactory.create(status=Statuses.in_progress)

        task_execute_and_complete(task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, Statuses.in_progress)

        m_logger.assert_called_once_with("Task %r has been already run", task.id)

    @patch("bptl.camunda.tasks.fail_task")
    @patch("bptl.camunda.tasks.complete")
    def test_task_execute_and_complete_fail_execute_retry_extend(
        self, m_complete, mock_fail_task
    ):

        task = ExternalTaskFactory.create()
        with patch(
            "bptl.camunda.tasks.execute", side_effect=TaskExpired("it expired")
        ) as mock_execute:
            with patch(
                "bptl.camunda.tasks.extend_task",
                side_effect=Exception("some exception"),
            ) as mock_extend_task:
                task_execute_and_complete(task.id)

        mock_execute.assert_called_once()
        mock_extend_task.assert_called_once()
        mock_fail_task.assert_called_once()

        task_execute_and_complete(task.id)

    @patch("bptl.camunda.tasks.complete")
    @requests_mock.Mocker()
    @freeze_time(timezone.make_aware(timezone.datetime(2020, 1, 2)))
    def test_task_execute_and_complete_fail_execute_retry_extend_success(
        self, m_complete, m
    ):
        config = CamundaConfig.get_solo()
        config.root_url = "https://some.camunda.com"
        config.rest_api_path = "engine-rest/"
        config.save()

        mapping = TaskMapping.objects.create(
            topic_name="zaak-initialize",
            callback="bptl.work_units.zgw.tasks.zaak.CreateZaakTask",
        )

        ZTC_URL = "https://some.ztc.nl/api/v1/"
        ZRC_URL = "https://some.zrc.nl/api/v1/"
        ZAAKTYPE = f"{ZTC_URL}zaaktypen/abcd"
        STATUSTYPE = f"{ZTC_URL}statustypen/7ff0bd9d-571f-47d0-8205-77ae41c3fc0b"
        ZAAK = f"{ZRC_URL}zaken/4f8b4811-5d7e-4e9b-8201-b35f5101f891"
        STATUS = f"{ZRC_URL}statussen/b7218c76-7478-41e9-a088-54d2f914a713"

        RESPONSES = {
            ZAAK: {
                "url": ZAAK,
                "uuid": "4f8b4811-5d7e-4e9b-8201-b35f5101f891",
                "identificatie": "ZAAK-2020-0000000013",
                "bronorganisatie": "002220647",
                "omschrijving": "",
                "zaaktype": ZAAKTYPE,
                "registratiedatum": "2020-01-16",
                "verantwoordelijkeOrganisatie": "002220647",
                "startdatum": "2020-01-16",
                "einddatum": None,
            },
        }

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

        task = ExternalTaskFactory.create(
            task_id="some-task-id",
            topic_name="zaak-initialize",
            variables={
                "zaaktype": serialize_variable(ZAAKTYPE),
                "organisatieRSIN": serialize_variable("123456788"),
                "bptlAppId": serialize_variable("some-app-id"),
            },
            lock_expires_at=timezone.make_aware(timezone.datetime(2020, 1, 1)),
        )

        # Mock camunda call and continue to complete
        m.post(
            f"https://some.camunda.com/engine-rest/external-task/some-task-id/extendLock",
            status_code=204,
        )
        m.get(
            f"https://some.camunda.com/engine-rest/external-task/some-task-id",
            status_code=200,
            json={
                "lock_expiration_time": timezone.make_aware(
                    timezone.datetime(2020, 1, 3)
                ).isoformat()
            },
        )

        # mock openzaak services
        mock_service_oas_get(m, ZTC_URL, "ztc")
        mock_service_oas_get(m, ZRC_URL, "zrc")
        m.get(
            f"{ZTC_URL}statustypen?zaaktype={ZAAKTYPE}",
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "url": STATUSTYPE,
                        "omschrijving": "initial",
                        "zaaktype": ZAAKTYPE,
                        "volgnummer": 1,
                        "isEindstatus": False,
                        "informeren": False,
                    },
                ],
            },
        )
        m.post(
            f"{ZRC_URL}zaken",
            status_code=201,
            json=RESPONSES[ZAAK],
        )
        m.post(
            f"{ZRC_URL}statussen",
            status_code=201,
            json={
                "url": STATUS,
                "uuid": "b7218c76-7478-41e9-a088-54d2f914a713",
                "zaak": ZAAK,
                "statustype": STATUSTYPE,
                "datumStatusGezet": "2020-01-16T00:00:00.000000Z",
                "statustoelichting": "",
            },
        )
        task.refresh_from_db()
        self.assertTrue(task.expired)

        task_execute_and_complete(task.id)
        task.refresh_from_db()

        # Task should not be expired
        self.assertFalse(task.expired)
        m_complete.assert_called_once()

    @patch("bptl.camunda.tasks.fail_task")
    @requests_mock.Mocker()
    @freeze_time(timezone.make_aware(timezone.datetime(2020, 1, 2)))
    def test_task_execute_and_complete_fail_execute_retry_could_not_be_extended(
        self, m_fail, m
    ):
        config = CamundaConfig.get_solo()
        config.root_url = "https://some.camunda.com"
        config.rest_api_path = "engine-rest/"
        config.save()

        mapping = TaskMapping.objects.create(
            topic_name="zaak-initialize",
            callback="bptl.work_units.zgw.tasks.zaak.CreateZaakTask",
        )

        task = ExternalTaskFactory.create(
            task_id="some-task-id",
            topic_name="zaak-initialize",
            lock_expires_at=timezone.make_aware(timezone.datetime(2020, 1, 1)),
        )

        # Mock camunda call and to fail
        m.post(
            f"https://some.camunda.com/engine-rest/external-task/some-task-id/extendLock",
            status_code=400,
        )

        task.refresh_from_db()
        self.assertTrue(task.expired)

        task_execute_and_complete(task.id)
        m_fail.assert_called_once()

    @patch("bptl.camunda.tasks.fail_task")
    @requests_mock.Mocker()
    @freeze_time(timezone.make_aware(timezone.datetime(2020, 1, 2)))
    def test_task_execute_and_complete_fail_execute_retry_false_extend(self, m_fail, m):
        config = CamundaConfig.get_solo()
        config.root_url = "https://some.camunda.com"
        config.rest_api_path = "engine-rest/"
        config.save()

        mapping = TaskMapping.objects.create(
            topic_name="zaak-initialize",
            callback="bptl.work_units.zgw.tasks.zaak.CreateZaakTask",
        )

        task = ExternalTaskFactory.create(
            task_id="some-task-id",
            topic_name="zaak-initialize",
            lock_expires_at=timezone.make_aware(timezone.datetime(2020, 1, 1)),
        )

        # Mock camunda call and to fail
        m.post(
            f"https://some.camunda.com/engine-rest/external-task/some-task-id/extendLock",
            status_code=204,
        )
        m.get(
            f"https://some.camunda.com/engine-rest/external-task/some-task-id",
            status_code=200,
            json={
                "lock_expiration_time": timezone.make_aware(
                    timezone.datetime(2020, 1, 1)
                ).isoformat()
            },
        )
        task.refresh_from_db()
        self.assertTrue(task.expired)

        task_execute_and_complete(task.id)
        m_fail.assert_called_once()
