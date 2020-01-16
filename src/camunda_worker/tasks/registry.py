"""
Manage a registry of tasks that can be used as callbacks.

A Task is a callable which takes a
:class:`camunda_worker.external_tasks.models.FetchedTask` instance as sole argument and
performs a unit of work.
"""
import inspect
from dataclasses import dataclass

from django.utils.module_loading import autodiscover_modules


@dataclass
class Task:
    dotted_path: str
    name: str
    documentation: str
    func: callable


class TaskRegistry:
    def __init__(self):
        self._registry = {}

    def __call__(self, func_or_class: callable):
        """
        Implement the decorator syntax.

        Applying the decorator to a callable registers it as a possible unit-of-work
        tasks to the registry.

        Registration performs some validation to enforce correct API usage,
        and grabs the docstring for a discription of the task.

        TODO: render docstring with sphinx
        """
        from camunda_worker.external_tasks.models import FetchedTask

        # check that there's one and only one expected argument
        sig = inspect.signature(func_or_class)
        if len(sig.parameters) != 1:
            raise TypeError(
                "A task must take exactly one argument - an instance of "
                "external_tasks.FetchedTask."
            )

        # check the expected type hint
        param = list(sig.parameters.values())[0]
        if param.annotation and not issubclass(param.annotation, FetchedTask):
            raise TypeError(
                f"The '{param.name}' typehint does not appear to be a FetchedTask"
            )

        dotted_path = f"{func_or_class.__module__}.{func_or_class.__qualname__}"
        self._registry[dotted_path] = Task(
            dotted_path=dotted_path,
            name=func_or_class.__class__,
            documentation=inspect.getdoc(func_or_class),
            func=func_or_class,
        )

    def autodiscover(self):
        autodiscover_modules("tasks", register_to=self)


# Sentinel to hold all tasks
register = TaskRegistry()
