"""
Manage a registry of tasks that can be used as callbacks.

A Task is a callable which takes an external task instance as sole argument and
performs a unit of work.
"""
import inspect
from dataclasses import dataclass

from django.utils.functional import cached_property
from django.utils.module_loading import autodiscover_modules
from django.utils.safestring import mark_safe

from .utils import render_docstring


@dataclass
class Task:
    dotted_path: str
    name: str
    documentation: str
    callback: callable

    @cached_property
    @mark_safe
    def html_documentation(self) -> str:
        """
        Return the docstring rendered as HTML by Sphinx.
        """
        return render_docstring(self.documentation)


@dataclass
class RequiredService:
    service_type: str
    description: str = ""
    alias: str = ""


class WorkUnitRegistry:
    def __init__(self):
        self._registry = {}

    def __call__(self, func_or_class: callable):
        """
        Implement the decorator syntax.

        Applying the decorator to a callable registers it as a possible unit-of-work
        tasks to the registry.

        Registration performs some validation to enforce correct API usage,
        and grabs the docstring for a discription of the task.
        """
        from .models import BaseTask

        # check that there's one and only one expected argument
        sig = inspect.signature(func_or_class)
        if len(sig.parameters) != 1:
            raise TypeError(
                "A task must take exactly one argument - an instance of "
                "tasks.BaseTask child class."
            )

        # check the expected type hint
        param = list(sig.parameters.values())[0]
        if param.annotation is not inspect._empty and not issubclass(
            param.annotation, BaseTask
        ):
            raise TypeError(
                f"The '{param.name}' typehint does not appear to be a BaseTask."
            )

        # check that classes have a perform method
        if inspect.isclass(func_or_class):
            if not hasattr(func_or_class, "perform"):
                raise TypeError(
                    f"The '{func_or_class}' class must have a `perform` method"
                )

        dotted_path = f"{func_or_class.__module__}.{func_or_class.__qualname__}"
        self._registry[dotted_path] = Task(
            dotted_path=dotted_path,
            name=func_or_class.__name__,
            documentation=inspect.getdoc(func_or_class) or "- docstring missing -",
            callback=func_or_class,
        )

        return func_or_class

    def __iter__(self):
        return iter(self._registry.values())

    def __getitem__(self, key: str):
        return self._registry[key]

    def require_service(
        self, service_type: str, description: str = "", alias: str = ""
    ):
        """
        Decorate a callback with the required service definitions.

        Used to validate the task mappings to ensure the required services are present.
        This self-documents which service aliases must be used for the callback to be
        able to function.
        """
        required_service = RequiredService(
            service_type=service_type, description=description, alias=alias
        )

        def decorator(func_or_class: callable):
            if not hasattr(func_or_class, "_required_services"):
                func_or_class._required_services = []
            func_or_class._required_services.append(required_service)
            return func_or_class

        return decorator

    def get_for(self, func_or_class: callable) -> str:
        """
        Retrieve the python dotted path for a given callable.
        """
        reverse = {
            task.callback: dotted_path for dotted_path, task in self._registry.items()
        }
        return reverse[func_or_class]

    def autodiscover(self):
        autodiscover_modules("tasks", register_to=self)


# Sentinel to hold all tasks
register = WorkUnitRegistry()
