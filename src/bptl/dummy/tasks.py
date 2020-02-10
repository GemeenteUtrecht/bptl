import logging

from bptl.external_tasks.camunda import complete_task
from bptl.external_tasks.models import FetchedTask
from bptl.tasks.registry import register

logger = logging.getLogger(__name__)


@register
def dummy(task: FetchedTask) -> None:
    """
    A dummy task to demonstrate the registry machinery.

    The task receives the :class:`FetchedTask` instance and logs some information,
    after which it completes the task.
    """
    logger.info("Received external task: %s", task.task_id)
    logger.info("External task currently hsa the variables: %r", task.flat_variables)
    logger.info("Marking task as completed...")
    complete_task(task)
