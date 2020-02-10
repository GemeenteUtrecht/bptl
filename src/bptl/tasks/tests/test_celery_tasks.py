from unittest.mock import patch

from django.test import TestCase

from bptl.external_tasks.tests.factories import FetchedTaskFactory

from ..tasks.celery import task_execute_and_complete, task_fetch_and_lock


class RouteTaskTests(TestCase):
    @patch("bptl.tasks.tasks.celery.task_execute_and_complete.delay")
    def test_task_fetch_and_lock(self, m_test_execute):
        task1, task2 = FetchedTaskFactory.create_batch(2, worker_id="aWorkerId")

        with patch(
            "bptl.tasks.tasks.celery.fetch_and_lock",
            return_value=("aWorkerId", 2, [task1, task2]),
        ) as m_fetch_and_lock:

            result = task_fetch_and_lock()

        self.assertEqual(result, 2)

        self.assertEqual(m_test_execute.call_count, 2)
        m_test_execute.assert_any_call(task1.id)
        m_test_execute.assert_any_call(task2.id)

    @patch("bptl.tasks.tasks.celery.complete")
    @patch("bptl.tasks.tasks.celery.execute")
    def test_task_execute_and_complete_success(self, m_execute, m_complete):
        task = FetchedTaskFactory.create()

        task_execute_and_complete(task.id)

        m_execute.assert_called_once_with(task)
        m_complete.assert_called_once_with(task)

    @patch("bptl.tasks.tasks.celery.complete")
    @patch("bptl.tasks.tasks.celery.execute", side_effect=Exception)
    def test_task_execute_and_complete_fail_execute(self, m_execute, m_complete):
        task = FetchedTaskFactory.create()

        task_execute_and_complete(task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, "failed")

        m_execute.assert_called_once_with(task)
        m_complete.assert_not_called()

    @patch("bptl.tasks.tasks.celery.complete", side_effect=Exception)
    @patch("bptl.tasks.tasks.celery.execute")
    def test_task_execute_and_complete_fail_complete(self, m_execute, m_complete):
        task = FetchedTaskFactory.create()

        task_execute_and_complete(task.id)

        task.refresh_from_db()
        self.assertEqual(task.status, "failed")

        m_execute.assert_called_once_with(task)
        m_complete.assert_called_once_with(task)
