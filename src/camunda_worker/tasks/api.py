"""
Expose the public API to manage tasks.
"""
import inspect

from camunda_worker.external_tasks.models import FetchedTask

from .models import TaskMapping
from .registry import TaskRegistry, register

__all__ = ["TaskExpired", "NoCallback", "execute"]


class TaskExpired(Exception):
    pass


class NoCallback(Exception):
    pass


def execute(task: FetchedTask, registry: TaskRegistry = register) -> None:
    """
    Execute the appropriate task for a fetched external task.

    This function takes care of looking up the appropriate handler for a task from the
    registry, and then calls it, passing the fetched task argument.

    :param task: A :class:`FetchedTask` instance, that may not have expired yet.
    :param registry: A :class:`camunda_worker.tasks.registry.TaskRegistry` instance.
      This is the registry that will be used to find the corresponding callback for the
      topic name. Defaults to the default sentinel registry, mostly useful for tests.
    :raises: :class:`TaskExpired` if the task is already expired, this exception is
      raised. You will need to re-fetch and lock the task before you can process it.
    :raises: :class:`NoCallback` if no callback could be determined for the topic.
    """
    # returns at most one result because of the unique constraint on topic_name
    task_mapping = TaskMapping.objects.filter(topic_name=task.topic_name).first()
    if task_mapping is None:
        raise NoCallback(
            f"Could not find a topic/callback mapping for topic {task.topic_name}"
        )

    try:
        handler = registry[task_mapping.callback]
    except KeyError as exc:
        raise NoCallback(
            f"Callback '{task_mapping.callback}' is not in the provided registry"
        ) from exc

    # actually call the task
    callback = handler.callback
    if inspect.isclass(callback):
        callback(task).perform()
    else:
        callback(task)
