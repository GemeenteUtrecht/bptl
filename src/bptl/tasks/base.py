from bptl.camunda.models import ExternalTask


class WorkUnit:
    def __init__(self, task: ExternalTask):
        self.task = task

    def perform(self) -> dict:
        raise NotImplementedError(
            "subclasses of WorkUnit must provide a perform() method"
        )

    def save_result(self, result_data: dict):
        self.task.result_variables = result_data
        self.task.save()
