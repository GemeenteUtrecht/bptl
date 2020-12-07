import warnings

from django.utils.translation import gettext_lazy as _

from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.tasks.base import BaseTask, check_variable
from bptl.tasks.registry import register
from bptl.work_units.zgw.tasks.base import NoService

from ..clients import get_client as _get_client
from ..services import get_alias_service
from .client import BRTClient

# support old situation until 1.1
API_ROOT = "https://brt.basisregistraties.overheid.nl/api/v2"

ALIAS = "BRT"

require_brt_service = register.require_service(
    APITypes.orc, description=_("The BRT instance to use."), alias=ALIAS
)


def get_brt_service(task: BaseTask) -> Service:
    """
    Extract the BRT Service object to use for the client.
    """
    try:
        return get_alias_service(task, ALIAS, service__api_type=APITypes.orc)
    except NoService:
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


def get_client(task: BaseTask) -> BRTClient:
    service = get_brt_service(task)
    return _get_client(task, service, cls=BRTClient)
