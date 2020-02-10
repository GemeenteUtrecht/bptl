import os

from django.test import TestCase

from bptl.camunda.models import ExternalTask


class FlatVariablesTests(TestCase):
    def test_process_flat_variables(self):
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
            },
        )

        self.assertEqual(
            task.flat_variables,
            {
                "zaaktype": "http://ztc.com/api/v1/zaaktypen/b38fbc9f-1273-4a0e-8189-cbec1b1f408f",
                "organisatieRSIN": "002220647",
            },
        )

    def test_process_flat_variables_none(self):
        task = ExternalTask.objects.create(
            worker_id="test-worker-id", task_id="test-task-id", variables={},
        )

        self.assertEqual(task.flat_variables, {})
