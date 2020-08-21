from django_camunda.api import send_message
from django_camunda.client import get_client

from bptl.camunda.models import ExternalTask

from .models import CreatedPackage


def on_package_complete(package_id: str) -> None:
    created_packages = CreatedPackage.objects.filter(package_id=package_id)
    if not created_packages:
        return

    camunda_client = get_client()

    for created_package in created_packages:
        task = created_package.task.get_real_instance()
        assert isinstance(task, ExternalTask), "Currently only Camunda is supported"

        message_id = task.get_variables().get("messageId")
        if not message_id:
            continue

        instance_id = task.instance_id
        if not instance_id:
            # we need to query the history because the task has been completed
            # NOTE: this requires history logging in Camunda!
            # TODO: we should store the process instance ID on the ExternalTask model instead
            external_task = camunda_client.get(
                f"history/external-task-log/{task.task_id}"
            )
            instance_id = external_task["processInstanceId"]

        # figure out the process instance ID
        send_message(message_id, [instance_id])
