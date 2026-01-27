from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


class UpdateTasksStatusTests(SimpleTestCase):
    def test_calls_partial_update_with_kwargs(self):
        """Test that _update_tasks_status passes data as keyword arguments."""
        from bptl.openklant.utils import _update_tasks_status

        mock_client = MagicMock()
        tasks = [
            {"url": "https://openklant.example.com/api/v1/internetaken/123"},
            {"url": "https://openklant.example.com/api/v1/internetaken/456"},
        ]

        _update_tasks_status(mock_client, tasks, status="verwerkt")

        self.assertEqual(mock_client.partial_update.call_count, 2)

        # Verify the first call
        call_args = mock_client.partial_update.call_args_list[0]
        self.assertEqual(call_args[0], ("internetaak",))  # positional args
        self.assertEqual(
            call_args[1],
            {
                "url": "https://openklant.example.com/api/v1/internetaken/123",
                "status": "verwerkt",
            },
        )

        # Verify the second call
        call_args = mock_client.partial_update.call_args_list[1]
        self.assertEqual(call_args[0], ("internetaak",))
        self.assertEqual(
            call_args[1],
            {
                "url": "https://openklant.example.com/api/v1/internetaken/456",
                "status": "verwerkt",
            },
        )


class UpdateTaskToelichtingInOpenklantTests(SimpleTestCase):
    @patch("bptl.openklant.utils.get_openklant_client")
    def test_calls_partial_update_with_kwargs(self, mock_get_client):
        """Test that _update_task_toelichting_in_openklant passes data as kwargs."""
        from bptl.openklant.utils import _update_task_toelichting_in_openklant

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        task = SimpleNamespace(
            variables={
                "url": "https://openklant.example.com/api/v1/internetaken/789",
                "toelichting": "Original toelichting",
            }
        )
        exception = Exception("Test error")

        _update_task_toelichting_in_openklant(task, exception)

        self.assertEqual(mock_client.partial_update.call_count, 1)

        call_args = mock_client.partial_update.call_args
        self.assertEqual(call_args[0], ("internetaak",))  # positional args

        # Check keyword arguments
        kwargs = call_args[1]
        self.assertEqual(
            kwargs["url"], "https://openklant.example.com/api/v1/internetaken/789"
        )
        self.assertIn("toelichting", kwargs)
        self.assertIn("[BPTL]", kwargs["toelichting"])
        self.assertIn("Mail versturen is mislukt.", kwargs["toelichting"])
        self.assertIn("Original toelichting", kwargs["toelichting"])


class UpdateTaskStatusTests(SimpleTestCase):
    def test_success_calls_partial_update_with_kwargs(self):
        """Test that update_task_status passes data as kwargs on success."""
        from bptl.openklant.tasks import update_task_status

        mock_client = MagicMock()
        failed_task = MagicMock()
        task = SimpleNamespace(
            variables={
                "url": "https://openklant.example.com/api/v1/internetaken/abc",
                "toelichting": "Some toelichting",
            }
        )

        update_task_status(failed_task, mock_client, task, success=True)

        self.assertEqual(mock_client.partial_update.call_count, 1)

        call_args = mock_client.partial_update.call_args
        self.assertEqual(call_args[0], ("internetaak",))  # positional args

        # Check keyword arguments
        kwargs = call_args[1]
        self.assertEqual(
            kwargs["url"], "https://openklant.example.com/api/v1/internetaken/abc"
        )
        self.assertIn("toelichting", kwargs)
        self.assertIn("[BPTL]", kwargs["toelichting"])
        self.assertIn("Succesvol afgerond", kwargs["toelichting"])

    def test_failure_does_not_call_partial_update(self):
        """Test that update_task_status does not call partial_update on failure."""
        from bptl.openklant.tasks import update_task_status

        mock_client = MagicMock()
        failed_task = MagicMock()
        task = SimpleNamespace(
            variables={
                "url": "https://openklant.example.com/api/v1/internetaken/abc",
            }
        )

        update_task_status(failed_task, mock_client, task, success=False)

        self.assertEqual(mock_client.partial_update.call_count, 0)
