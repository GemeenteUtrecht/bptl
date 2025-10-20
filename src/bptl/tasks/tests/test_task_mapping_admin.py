from unittest.mock import patch

from django.urls import reverse

from django_webtest import WebTest

from bptl.accounts.models import User
from bptl.tests.utils import get_admin_form

from ..registry import WorkUnitRegistry

test_register = WorkUnitRegistry()


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
        patcher = patch("bptl.tasks.forms.register", new=test_register)
        self.mocked_register = patcher.start()
        self.addCleanup(patcher.stop)

    def test_show_select_registered_tasks(self):
        url = reverse("admin:tasks_taskmapping_add")
        add_page = self.app.get(url)
        self.assertEqual(add_page.status_code, 200)

        html = add_page.text
        self.assertInHTML("task1", html)
        self.assertInHTML("Task 1 documentation", html)
        self.assertInHTML("task2", html)
        self.assertInHTML("Task 2 documentation", html)

        form = get_admin_form(add_page)

        form["topic_name"] = "foo"
        callback_field = form["callback"]
        callback_field.select("bptl.tasks.tests.test_task_mapping_admin.task2")

        submitted = form.submit()
        self.assertEqual(submitted.status_code, 302)
