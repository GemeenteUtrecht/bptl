from django.test import TestCase

from bptl.tasks.base import check_variable


class CheckVariableTest(TestCase):
    def test_check_bool_variable_true(self):
        variables = {"test_var": True}

        test_var = check_variable(variables, "test_var")

        self.assertTrue(test_var)

    def test_check_bool_variable_false(self):
        variables = {"test_var": False}

        test_var = check_variable(variables, "test_var")

        self.assertFalse(test_var)
