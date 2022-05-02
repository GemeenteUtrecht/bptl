import warnings
from typing import List

from django.utils.translation import gettext_lazy as _

from zgw_consumers.client import ZGWClient
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from bptl.credentials.api import get_credentials
from bptl.tasks.models import BaseTask
from bptl.tasks.registry import register

from ..clients import APP_ID_PROCESS_VAR_NAME
from ..services import get_alias_service

ALIAS = "ValidSignAPI"

require_validsign_service = register.require_service(
    APITypes.orc,
    description=_("The ValidSign API to use."),
    alias=ALIAS,
)


def get_client(task: BaseTask) -> ZGWClient:
    service = get_alias_service(task, ALIAS)

    client = service.build_client()
    client._log.task = task

    # set the auth if we have the bptlAppId set
    app_id = task.get_variables().get(APP_ID_PROCESS_VAR_NAME)
    if app_id:
        auth_headers = get_credentials(app_id, service)[service]
        if auth_headers:
            client.set_auth_value(auth_headers)

    # export the client
    return client


class DRCClientPool:
    def __init__(self, task_variables: dict):
        self.app_id = task_variables.get(APP_ID_PROCESS_VAR_NAME)

        self._clients = []  # mapping of API root to service, works as a cache

    def populate_clients(self, task, document_urls: List[str]) -> None:
        # fetch all the DRC services, single query
        drcs = Service.objects.filter(api_type=APITypes.drc)
        # only keep the DRCs that we actually need
        _relevant_drcs = []
        for drc in drcs:
            if any(doc.startswith(drc.api_root) for doc in document_urls):
                _relevant_drcs.append(drc)
                continue

        # build the clients
        service_credentials = get_credentials(self.app_id, *_relevant_drcs)
        for drc in sorted(
            _relevant_drcs, key=lambda svc: len(svc.api_root), reverse=True
        ):
            client = drc.build_client()

            auth_headers = service_credentials.get(drc)
            client.set_auth_value(auth_headers)
            client._log.task = task
            self._clients.append(client)

    def get_client_for(self, document_url: str) -> ZGWClient:
        for client in self._clients:
            if document_url.startswith(client.base_url):
                return client
        else:
            service = Service.get_service(document_url)
            auth_headers = get_credentials(self.app_id, service).get(service)
            client = service.build_client()
            if auth_headers:
                client.set_auth_value(auth_headers)
            return client
