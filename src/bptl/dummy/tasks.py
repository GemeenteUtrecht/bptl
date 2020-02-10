import logging

from bptl.camunda.models import ExternalTask
from bptl.camunda.utils import complete_task
from bptl.tasks.registry import register

logger = logging.getLogger(__name__)


@register
def dummy(task: ExternalTask) -> None:
    """
    A dummy task to demonstrate the registry machinery.

    The task receives the :class:`ExternalTask` instance and logs some information,
    after which it completes the task.
    """
    logger.info("Received external task: %s", task.task_id)
    logger.info("External task currently hsa the variables: %r", task.flat_variables)
    logger.info("Marking task as completed...")
    complete_task(task)
