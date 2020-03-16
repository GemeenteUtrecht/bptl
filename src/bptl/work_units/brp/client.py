"""
Implements a BRP client.
"""
import logging
from urllib.parse import urljoin

from django.conf import settings
from django.utils.module_loading import import_string

import requests
from timeline_logger.models import TimelineLog

from .models import BRPConfig

logger = logging.getLogger(__name__)


def get_client_class() -> type:
    client_class = getattr(
        settings, "BRP_CLIENT_CLASS", "bptl.work_units.brp.client.BRPClient"
    )
    return import_string(client_class)


class BRPClient:
    task = None

    def __init__(self, config=None):
        self.config = config or BRPConfig.get_solo()
        self.api_root = self.config.api_root
        self.auth = self.config.auth_header

    def get(self, path: str, *args, **kwargs):
        url = urljoin(self.api_root, path)

        # add the API headers
        headers = kwargs.pop("headers", {})
        headers.update(self.auth)
        kwargs["headers"] = headers
        params = kwargs.get("params")

        response = requests.get(url, *args, **kwargs)

        # can't use requests.hooks, therefore direct logging
        self.log(response, params)

        response.raise_for_status()

        return response.json()

    def log(self, resp, params):
        config = BRPConfig.get_solo()
        response_data = resp.json() if resp.content else None

        extra_data = {
            "service_base_url": config.api_root,
            "request": {
                "url": resp.url,
                "method": resp.request.method,
                "headers": dict(resp.request.headers),
                "data": resp.request.body,
                "params": params,
            },
            "response": {
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "data": response_data,
            },
        }
        TimelineLog.objects.create(content_object=self.task, extra_data=extra_data)
