from django.test import TestCase

from bptl.camunda.models import ExternalTask


class FlatVariablesTests(TestCase):
    def test_get_variables(self):
        task = ExternalTask.objects.create(
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "zaaktype": {
                    "type": "String",
                    "value": "http://ztc.com/api/v1/zaaktypen/b38fbc9f-1273-4a0e-8189-cbec1b1f408f",
                    "valueInfo": {},
                },
                "organisatieRSIN": {
                    "type": "String",
                    "value": "002220647",
                    "valueInfo": {},
                },
                "foo": {"type": "Json", "value": '{"bar":"baz"}', "valueInfo": {},},
            },
        )

        self.assertEqual(
            task.get_variables(),
            {
                "zaaktype": "http://ztc.com/api/v1/zaaktypen/b38fbc9f-1273-4a0e-8189-cbec1b1f408f",
                "organisatieRSIN": "002220647",
                "foo": {"bar": "baz",},
            },
        )

    def test_get_variables_none(self):
        task = ExternalTask.objects.create(
            worker_id="test-worker-id", task_id="test-task-id", variables={},
        )

        self.assertEqual(task.get_variables(), {})
