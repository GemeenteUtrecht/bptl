"""
Implements a ZAC client.
"""
import logging

from django.utils.translation import gettext_lazy as _

from zgw_consumers.constants import APITypes

from bptl.credentials.api import get_credentials
from bptl.tasks.models import BaseTask
from bptl.tasks.registry import register

from ..clients import JSONClient
from ..services import get_alias_service

logger = logging.getLogger(__name__)

ALIAS = "zac"

PROCESS_VAR_NAME = "bptlAppId"

require_zac_service = register.require_service(
    APITypes.orc,
    description=_("The ZAC API to use."),
    alias=ALIAS,
)


def get_client(task: BaseTask) -> "ZACClient":
    # get the service and credentials
    service = get_alias_service(task, ALIAS)
    app_id = task.get_variables().get(PROCESS_VAR_NAME)
    auth_header = get_credentials(app_id, service)[service] if app_id else {}
    if not auth_header:
        auth_header = service.build_client().auth_header

    # export the client
    client = ZACClient(service, auth_header)
    client.task = task
    return client


class ZACClient(JSONClient):
    pass
