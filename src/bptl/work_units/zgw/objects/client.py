"""
Implements an OBJECTS client.

"""
import logging

from django.utils.translation import gettext_lazy as _

from zgw_consumers.constants import APITypes

from bptl.tasks.models import BaseTask
from bptl.tasks.registry import register
from bptl.work_units.clients import JSONClient, get_client as _get_client
from bptl.work_units.services import get_alias_service

logger = logging.getLogger(__name__)

OBJECTS_ALIAS = "objects"

require_objects_service = register.require_service(
    APITypes.orc,
    description=_("The OBJECTS API to use."),
    alias=OBJECTS_ALIAS,
)


def get_objects_client(task: BaseTask) -> "ObjectsClient":
    # get the service and credentials
    service = get_alias_service(task, OBJECTS_ALIAS)
    return _get_client(task, service, cls=ObjectsClient)


class ObjectsClient(JSONClient):
    pass
