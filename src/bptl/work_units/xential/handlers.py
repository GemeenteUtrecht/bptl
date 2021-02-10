from django_camunda.api import send_message
from django_camunda.client import get_client

from bptl.camunda.models import ExternalTask
from bptl.tasks.models import BaseTask


def on_document_created(task: BaseTask, document_url: str) -> None:
    camunda_client = get_client()
    task = task.get_real_instance()
    assert isinstance(task, ExternalTask), "Currently only Camunda is supported"

    message_id = task.get_variables().get("messageId")
    if not message_id:
        return

    instance_id = task.instance_id
    if not instance_id:
        external_task = camunda_client.get(f"history/external-task-log/{task.task_id}")
        instance_id = external_task["process_instance_id"]

    send_message(message_id, [instance_id], variables={"url": document_url})
