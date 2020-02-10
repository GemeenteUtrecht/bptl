"""
Expose the public API to manage tasks.
"""
import inspect

from bptl.camunda.constants import Statuses
from bptl.camunda.models import ExternalTask
from bptl.camunda.utils import complete_task

from .models import TaskMapping
from .registry import TaskRegistry, register

__all__ = [
    "TaskExpired",
    "NoCallback",
    "TaskPerformed",
    "TaskNotPerformed",
    "execute",
    "complete",
]


class TaskExpired(Exception):
    pass


class NoCallback(Exception):
    pass


class TaskPerformed(Exception):
    pass


class TaskNotPerformed(Exception):
    pass


def execute(task: ExternalTask, registry: TaskRegistry = register) -> None:
    """
    Execute the appropriate task for a fetched external task.

    This function takes care of looking up the appropriate handler for a task from the
    registry, and then calls it, passing the fetched task argument.

    :param task: A :class:`ExternalTask` instance, that may not have expired yet.
    :param registry: A :class:`bptl.tasks.registry.TaskRegistry` instance.
      This is the registry that will be used to find the corresponding callback for the
      topic name. Defaults to the default sentinel registry, mostly useful for tests.
    :raises: :class:`TaskExpired` if the task is already expired, this exception is
      raised. You will need to re-fetch and lock the task before you can process it.
    :raises: :class:`NoCallback` if no callback could be determined for the topic.
    :raises: :class:`TaskPerformed` if the task is already completed, this exception is
      raised.
    """
    # returns at most one result because of the unique constraint on topic_name
    task_mapping = TaskMapping.objects.filter(topic_name=task.topic_name).first()
    if task_mapping is None:
        raise NoCallback(
            f"Could not find a topic/callback mapping for topic '{task.topic_name}'."
        )

    try:
        handler = registry[task_mapping.callback]
    except KeyError as exc:
        raise NoCallback(
            f"Callback '{task_mapping.callback}' is not in the provided registry."
        ) from exc

    # check task status
    if task.status in [Statuses.completed, Statuses.performed]:
        raise TaskPerformed(f"The task {task} has been already performed.")

    # check for expiry
    if task.expired:
        raise TaskExpired(f"The task {task} expired before it could be handled.")

    # actually call the task
    callback = handler.callback
    if inspect.isclass(callback):
        callback(task).perform()
    else:
        callback(task)

    # set complete status
    task.status = Statuses.performed
    task.save()


def complete(task: ExternalTask):
    """
    Send the result of a fetched task into Camunda.

    :param task: A :class:`ExternalTask` instance, that has been already performed.
    :raises: :class:`TaskNotPerformed` if the task status is not "performed", this exception is
      raised.
    """
    if task.status != Statuses.performed:
        raise TaskNotPerformed(
            f"The task {task} is {task.status}. The task should be performed before sending results"
        )

    complete_task(task)

    task.status = Statuses.completed
    task.save()
