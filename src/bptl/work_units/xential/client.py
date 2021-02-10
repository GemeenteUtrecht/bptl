"""
Implements a Xential client.
"""
import logging
from typing import Dict, List

from django.utils.translation import gettext_lazy as _

from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from bptl.tasks.models import BaseTask
from bptl.tasks.registry import register

from ..clients import JSONClient, get_client as _get_client
from ..services import get_alias_service

logger = logging.getLogger(__name__)

XENTIAL_ALIAS = "xential"
DRC_ALIAS = "DRC"

require_xential_service = register.require_service(
    APITypes.orc,
    description=_("The Xential API to use."),
    alias=XENTIAL_ALIAS,
)

require_drc_service = register.require_service(
    APITypes.drc,
    description=_("The DRC API to use."),
    alias=DRC_ALIAS,
)


class XentialClient(JSONClient):
    def __init__(self, service: Service, auth_header: Dict[str, str]):
        super().__init__(service, auth_header)

        self.cookie_header = self.set_cookie_header()

    def set_cookie_header(self) -> str:
        xsession_id_url = "auth/whoami"
        response_data = self.request("post", xsession_id_url, use_cookie_header=False)
        return f"XSessionID={response_data['XSessionId']}"

    def request(self, method: str, path: str, use_cookie_header=True, **kwargs):
        if use_cookie_header:
            headers = kwargs.pop("headers", {})
            headers.setdefault("Cookie", self.cookie_header)
            kwargs["headers"] = headers

        return super().request(method, path, **kwargs)


def get_client(task: BaseTask, alias: str) -> "JSONClient":
    client_classes = {XENTIAL_ALIAS: XentialClient}
    # get the service and credentials
    service = get_alias_service(task, alias)
    return _get_client(task, service, cls=client_classes.get(alias))


def get_default_clients(alias: str) -> List["JSONClient"]:
    # get the service and default credentials
    # we can't use zgw_consumers client, since it uses OAS
    clients = [
        JSONClient(service, service.build_client().auth_header)
        for service in Service.objects.filter(defaultservice__alias=alias).distinct()
    ]
    return clients
