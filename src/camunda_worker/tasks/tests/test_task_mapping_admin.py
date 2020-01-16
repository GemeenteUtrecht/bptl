from unittest.mock import patch

from django.urls import reverse

from django_webtest import WebTest

from camunda_worker.accounts.models import User

from ..registry import TaskRegistry

# Set up an isolated registry for tests
test_register = TaskRegistry()


@test_register
def task1(task):
    """Task 1 documentation"""
    pass


@test_register
def task2(task):
    """Task 2 documentation"""
    pass


class TaskMappingCreateTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("super", "user@utrecht.nl", "letmein")

    def setUp(self):
        self.app.set_user(self.user)

        patcher = patch("camunda_worker.tasks.forms.register", new=test_register)
        self.mocked_register = patcher.start()
        self.addCleanup(patcher.stop)

    def test_show_select_registered_tasks(self):
        url = reverse("admin:tasks_taskmapping_add")

        add_page = self.app.get(url)

        html = add_page.text
        self.assertInHTML("task1", html)
        self.assertInHTML("Task 1 documentation", html)
        self.assertInHTML("task2", html)
        self.assertInHTML("Task 2 documentation", html)

        add_page.form["topic_name"] = "foo"
        callback_field = add_page.form["callback"]
        callback_field.select(
            "camunda_worker.tasks.tests.test_task_mapping_admin.task2"
        )

        submitted = add_page.form.submit()
        self.assertEqual(submitted.status_code, 302)
