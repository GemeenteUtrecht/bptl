import warnings

from django.utils.translation import gettext_lazy as _

from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.credentials.api import get_credentials
from bptl.tasks.base import BaseTask, check_variable
from bptl.tasks.models import DefaultService
from bptl.tasks.registry import register

from .client import BRTClient

# support old situation until 1.1
API_ROOT = "https://brt.basisregistraties.overheid.nl/api/v2"

ALIAS = "BRT"
PROCESS_VAR_NAME = "bptlAppId"

require_brt_service = register.require_service(
    APITypes.orc, description=_("The BRT instance to use."), alias=ALIAS
)


def get_brt_service(task: BaseTask) -> Service:
    """
    Extract the BRT Service object to use for the client.
    """
    try:
        default_service = (
            DefaultService.objects.filter(
                task_mapping__topic_name=task.topic_name,
                service__api_type=APITypes.orc,
                alias=ALIAS,
            )
            .select_related("service")
            .get()
        )
    except DefaultService.DoesNotExist:
        warnings.warn(
            "Falling back to static configuration, this support will be removed "
            "in BPTL 1.1",
            DeprecationWarning,
        )
        variables = task.get_variables()
        return Service(
            api_root=API_ROOT,
            label="BRT",
            auth_type=AuthTypes.api_key,
            header_key="X-Api-Key",
            header_value=check_variable(variables, "BRTKey"),
            oas=API_ROOT,
        )
    return default_service.service


def get_client(task: BaseTask) -> BRTClient:
    service = get_brt_service(task)
    app_id = task.get_variables().get(PROCESS_VAR_NAME)
    auth_header = get_credentials(app_id, service)[service] if app_id else {}
    if not auth_header:
        auth_header = service.build_client().auth_header

    # export the client
    client = BRTClient(service, auth_header)
    client.task = task
    return client
