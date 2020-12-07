"""
Implements a BRP client.
"""
import logging

from django.utils.translation import gettext_lazy as _

from zgw_consumers.constants import APITypes

from bptl.tasks.models import BaseTask
from bptl.tasks.registry import register

from ..clients import JSONClient, get_client as _get_client
from ..services import get_alias_service

logger = logging.getLogger(__name__)

ALIAS = "brp"

require_brp_service = register.require_service(
    APITypes.orc,
    description=_("The BRP API to use."),
    alias=ALIAS,
)


def get_client(task: BaseTask) -> "BRPClient":
    # get the service and credentials
    service = get_alias_service(task, ALIAS)
    return _get_client(task, service, cls=BRPClient)


class BRPClient(JSONClient):
    pass
