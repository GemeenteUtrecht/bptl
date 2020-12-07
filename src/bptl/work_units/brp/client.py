"""
Implements a BRP client.
"""
import logging
from typing import Dict
from urllib.parse import urljoin

from django.utils.translation import gettext_lazy as _

import requests
from timeline_logger.models import TimelineLog
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from bptl.credentials.api import get_credentials
from bptl.tasks.models import BaseTask, DefaultService
from bptl.tasks.registry import register
from bptl.work_units.zgw.tasks.base import NoService

logger = logging.getLogger(__name__)

ALIAS = "brp"

PROCESS_VAR_NAME = "bptlAppId"

require_brp_service = register.require_service(
    APITypes.orc,
    description=_("The BRP API to use."),
    alias=ALIAS,
)


def get_brp_service(task: BaseTask) -> Service:
    """
    Extract the BRP Service object to use for the client.
    """
    try:
        default_service = DefaultService.objects.filter(
            task_mapping__topic_name=task.topic_name, alias=ALIAS
        ).get()
    except DefaultService.DoesNotExist:
        raise NoService(f"No '{ALIAS}' service configured.")
    return default_service.service


def get_client(task: BaseTask) -> "BRPClient":
    # get the service and credentials
    service = get_brp_service(task)
    app_id = task.get_variables().get(PROCESS_VAR_NAME)
    auth_header = get_credentials(app_id, service)[service] if app_id else {}
    if not auth_header:
        auth_header = service.build_client().auth_header

    # export the client
    client = BRPClient(service, auth_header)
    client.task = task
    return client


class BRPClient:
    task = None

    def __init__(self, service: Service, auth_header: Dict[str, str]):
        self.api_root = service.api_root
        self.auth = auth_header

    def get(self, path: str, *args, **kwargs):
        url = urljoin(self.api_root, path)

        # add the API headers
        headers = kwargs.pop("headers", {})
        headers.update(self.auth)
        kwargs["headers"] = headers
        kwargs["hooks"] = {"response": self.log}

        response = requests.get(url, *args, **kwargs)
        response.raise_for_status()

        return response.json()

    def log(self, resp, *args, **kwargs):
        response_data = resp.json() if resp.content else None

        extra_data = {
            "service_base_url": self.api_root,
            "request": {
                "url": resp.url,
                "method": resp.request.method,
                "headers": dict(resp.request.headers),
                "data": resp.request.body,
                "params": resp.request.qs,
            },
            "response": {
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "data": response_data,
            },
        }
        TimelineLog.objects.create(content_object=self.task, extra_data=extra_data)
