from .models import BaseTask


class WorkUnit:
    def __init__(self, task: BaseTask):
        self.task = task

    def perform(self) -> dict:
        raise NotImplementedError(
            "subclasses of WorkUnit must provide a perform() method"
        )
