"""
Implements a ZAC client.
"""
import logging

from django.utils.translation import gettext_lazy as _

from zgw_consumers.constants import APITypes

from bptl.tasks.models import BaseTask
from bptl.tasks.registry import register
from bptl.work_units.clients import JSONClient, get_client as _get_client
from bptl.work_units.services import get_alias_service

logger = logging.getLogger(__name__)

ALIAS = "zac"

require_zac_service = register.require_service(
    APITypes.orc,
    description=_("The ZAC API to use."),
    alias=ALIAS,
)


def get_client(task: BaseTask) -> "ZACClient":
    # get the service and credentials
    service = get_alias_service(task, ALIAS)
    return _get_client(task, service, cls=ZACClient)


class ZACClient(JSONClient):
    pass
