"""
Expose the public API to manage tasks.
"""
from camunda_worker.external_tasks.models import FetchedTask

from .registry import register

__all__ = ["TaskExpired", "execute"]


class TaskExpired(Exception):
    pass


def execute(task: FetchedTask, registry=register):
    """
    Execute the appropriate task for a fetched external task.

    This function takes care of looking up the appropriate handler for a task from the
    registry, and then calls it, passing the fetched task argument.

    :param task: A :class:`FetchedTask` instance, that may not have expired yet.
    :param registry: A :class:`camunda_worker.tasks.registry.TaskRegistry` instance.
      This is the registry that will be used to find the corresponding callback for the
      topic name. Defaults to the default sentinel registry, mostly useful for tests.
    :raises: :class:`TaskExpired` - if the task is already expired, this exception is
      raised. You will need to re-fetch and lock the task before you can process it.
    """
    pass
