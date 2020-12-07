from django.utils.translation import gettext_lazy as _

from zgw_consumers.client import ZGWClient
from zgw_consumers.constants import APITypes

from bptl.credentials.api import get_credentials
from bptl.tasks.models import BaseTask
from bptl.tasks.registry import register
from bptl.work_units.zgw.models import DefaultService
from bptl.work_units.zgw.tasks.base import NoService

ALIAS = "ValidSignAPI"

PROCESS_VAR_NAME = "bptlAppId"

require_validsign_service = register.require_service(
    APITypes.orc,
    description=_("The ValidSign API to use."),
    alias=ALIAS,
)


def get_client(task: BaseTask) -> ZGWClient:
    # get the service and credentials
    try:
        default_service = DefaultService.objects.filter(
            task_mapping__topic_name=task.topic_name,
            alias=ALIAS,
        ).get()
    except DefaultService.DoesNotExist:
        raise NoService(f"No '{ALIAS}' service configured.")

    service = default_service.service

    client = service.build_client()
    client._log.task = task

    # set the auth if we have the bptlAppId set
    app_id = task.get_variables().get(PROCESS_VAR_NAME)
    if app_id:
        auth_headers = get_credentials(app_id, service)[service]
        if auth_headers:
            client.set_auth_value(auth_headers)

    # export the client
    return client
