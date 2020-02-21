from .models import BaseTask


class WorkUnit:
    def __init__(self, task: BaseTask):
        self.task = task

    def perform(self) -> dict:
        raise NotImplementedError(
            "subclasses of WorkUnit must provide a perform() method"
        )

    def save_result(self, result_data: dict):
        self.task.result_variables = result_data
        self.task.save(update_fields=["result_variables"])
