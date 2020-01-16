"""
Test the expected implementation of the registry.
"""
from django.test import SimpleTestCase

from camunda_worker.external_tasks.models import FetchedTask

from ..registry import TaskRegistry

# isolated registry for tests
register = TaskRegistry()


class FunctionRegistryTests(SimpleTestCase):
    def test_no_arguments(self):
        def task():
            pass

        with self.assertRaises(TypeError):
            register(task)

    def test_multiple_arguments(self):
        def task(arg1, arg2):
            pass

        with self.assertRaises(TypeError):
            register(task)

    def test_no_typehint(self):
        def task(task):
            pass

        try:
            register(task)
        except TypeError:
            self.fail("Task should have been registered")

    def test_wrong_typehint(self):
        def task(task: TaskRegistry):
            pass

        with self.assertRaises(TypeError):
            register(task)

    def test_correct_typehint(self):
        def task(task: FetchedTask):
            pass

        try:
            register(task)
        except TypeError:
            self.fail("Task should have been registered")


class ClassRegistryTests(SimpleTestCase):
    def test_no_init_params(self):
        class Task:
            pass

        with self.assertRaises(TypeError):
            register(Task)

    def test_multiple_params(self):
        class Task:
            def __init__(self, task, arg2):
                self.task = task

        with self.assertRaises(TypeError):
            register(Task)

    def test_no_typehint(self):
        class Task:
            def __init__(self, task):
                self.task = task

            def perform(self):
                pass

        try:
            register(Task)
        except TypeError:
            self.fail("Task should have been registered")

    def test_wrong_typehint(self):
        class Task:
            def __init__(self, task: TaskRegistry):
                self.task = task

        with self.assertRaises(TypeError):
            register(Task)

    def test_correct_typehint(self):
        class Task:
            def __init__(self, task: FetchedTask):
                self.task = task

            def perform(self):
                pass

        try:
            register(Task)
        except TypeError:
            self.fail("Task should have been registered")

    def test_missing_perform_method(self):
        class Task:
            def __init__(self, task):
                self.task = task

        with self.assertRaises(TypeError):
            register(Task)


class TaskRegistryTests(SimpleTestCase):
    def test_introspection(self):
        def sample_task(task):
            """
            Sample docstring.
            """
            pass

        register(sample_task)

        dotted_path = f"{sample_task.__module__}.{sample_task.__qualname__}"
        task = register[dotted_path]
        self.assertEqual(task.name, "sample_task")
        self.assertEqual(task.documentation, "Sample docstring.")
        self.assertEqual(task.dotted_path, dotted_path)
