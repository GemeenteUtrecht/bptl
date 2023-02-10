from zgw_consumers.models import Service

from bptl.tasks.models import BaseTask, DefaultService
from bptl.work_units.zgw.client import NoService


def get_alias_service(task: BaseTask, alias: str, **extra_filters) -> Service:
    """
    Given a task and alias, find the matching :class:`Service` instance.

    :param alias: The particular alias-service to retrieve for the task
    :param extra_filters: Any extra queryset filters to apply.

    If no service is found, :class:`NoService` is raised.
    """
    try:
        default_service = DefaultService.objects.filter(
            task_mapping__topic_name=task.topic_name,
            alias=alias,
            **extra_filters,
        ).get()
    except DefaultService.DoesNotExist:
        raise NoService(f"No '{alias}' service configured.")
    return default_service.service
