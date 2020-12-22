"""
Provide base client implementations, based on requests.

Note that for the time being only get/post are implemented.
"""
import json
from typing import Dict
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from timeline_logger.models import TimelineLog
from zgw_consumers.models import Service

from bptl.credentials.api import get_credentials
from bptl.tasks.base import BaseTask

APP_ID_PROCESS_VAR_NAME = "bptlAppId"


def get_client(task: BaseTask, service: Service, cls=None) -> "JSONClient":
    """
    Get a client instance for the given task and service.

    :param task: An instance of the work unit task being executed
    :param service: The service to build an authenticated client for
    :param cls: The particular (sub)class to use for the client instance. Defaults to
      :class:`JSONClient`.
    """
    cls = cls or JSONClient
    app_id = task.get_variables().get(APP_ID_PROCESS_VAR_NAME)
    auth_header = get_credentials(app_id, service)[service] if app_id else {}

    # export the client
    client = cls(service, auth_header)
    client.task = task
    return client


class JSONClient:
    task = None

    def __init__(self, service: Service, auth_header: Dict[str, str]):
        self.api_root = service.api_root
        self.auth = auth_header
        self.session = requests.Session()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.__exit__(*args)

    def request(self, method: str, path: str, **kwargs):
        assert not path.startswith("/"), "Only relative paths are supported."
        url = urljoin(self.api_root, path)
        # add the API headers
        headers = kwargs.pop("headers", {})
        headers.setdefault("Accept", "application/json")
        headers.update(self.auth)
        kwargs["headers"] = headers
        kwargs["hooks"] = {"response": self.log}

        response = self.session.request(method=method, url=url, **kwargs)
        response.raise_for_status()
        return response.json()

    def get(self, path: str, params=None, **kwargs):
        kwargs.setdefault("allow_redirects", True)
        return self.request("get", path, params=params, **kwargs)

    def post(self, path: str, data=None, json=None, **kwargs):
        return self.request("post", path, data=data, json=json, **kwargs)

    def log(self, resp, *args, **kwargs):
        response_data = resp.json() if resp.content else None

        body = json.loads(resp.request.body) if resp.request.body else None
        extra_data = {
            "service_base_url": self.api_root,
            "request": {
                "url": resp.url,
                "method": resp.request.method,
                "headers": dict(resp.request.headers),
                "data": body,
                "params": parse_qs(urlparse(resp.request.url).query),
            },
            "response": {
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "data": response_data,
            },
        }
        TimelineLog.objects.create(content_object=self.task, extra_data=extra_data)
