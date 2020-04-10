from .models import BaseTask


class MissingVariable(Exception):
    pass


def check_variable(variables: dict, name: str, empty_allowed=False):
    error = MissingVariable(f"The variable {name} is missing or empty.")
    if name not in variables:
        raise error

    elif not empty_allowed and not variables[name]:
        raise error

    return variables[name]


class WorkUnit:
    def __init__(self, task: BaseTask):
        self.task = task

    def perform(self) -> dict:
        raise NotImplementedError(
            "subclasses of WorkUnit must provide a perform() method"
        )
