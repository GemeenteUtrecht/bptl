"""
Implements a Xential client.
"""
import logging
from typing import List

from django.utils.translation import gettext_lazy as _

from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from bptl.tasks.models import BaseTask
from bptl.tasks.registry import register

from ..clients import JSONClient, get_client as _get_client
from ..services import get_alias_service

logger = logging.getLogger(__name__)

ALIAS = "xential"

require_xential_service = register.require_service(
    APITypes.orc,
    description=_("The Xential API to use."),
    alias=ALIAS,
)


def get_client(task: BaseTask) -> "JSONClient":
    # get the service and credentials
    service = get_alias_service(task, ALIAS)
    return _get_client(task, service)


def get_default_clients() -> List["JSONClient"]:
    # get the service and default credentials
    # we can't use zgw_consumers client, since it uses OAS
    clients = [
        JSONClient(service, service.build_client().auth_header)
        for service in Service.objects.filter(defaultservice__alias=ALIAS).distinct()
    ]
    return clients
