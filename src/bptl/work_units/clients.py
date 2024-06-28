"""
Provide base client implementations, based on requests.

Note that for the time being only get/post are implemented.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from requests.structures import CaseInsensitiveDict
from timeline_logger.models import TimelineLog
from zds_client.oas import schema_fetcher
from zds_client.schema import get_headers
from zgw_consumers.models import Service

from bptl.credentials.api import get_credentials
from bptl.tasks.base import BaseTask

logger = logging.getLogger(__name__)

APP_ID_PROCESS_VAR_NAME = "bptlAppId"

Object = Dict[str, Any]


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
    auth_header = get_credentials(app_id, service)[service]

    # export the client
    client = cls(service, auth_header)
    client.task = task
    return client


class JSONClient:
    """
    Adapted to include operation method from zds_client.Client.

    """

    task = None
    _schema = None

    @property
    def schema(self):
        if self._schema is None:
            self.fetch_schema()
        return self._schema

    def fetch_schema(self) -> None:
        url = urljoin(self.api_root, "schema/openapi.yaml")
        logger.info("Fetching schema at '%s'", url)
        self._schema = schema_fetcher.fetch(url, {"v": "3"})

    def __init__(self, service: Service, auth_header: Dict[str, str]):
        self.api_root = service.api_root
        self.auth = auth_header
        self.session = requests.Session()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.__exit__(*args)

    def request(
        self,
        method: str,
        path: str,
        operation: str = "",
        request_kwargs: Optional[Dict] = None,
        **kwargs,
    ) -> Optional[Dict]:
        assert not path.startswith("/"), "Only relative paths are supported."
        url = urljoin(self.api_root, path)

        if request_kwargs:
            kwargs.update(request_kwargs)

        headers = CaseInsensitiveDict(kwargs.pop("headers", {}))
        headers.setdefault("Accept", "application/json")

        if operation:
            schema_headers = get_headers(self.schema, operation)
            for header, value in schema_headers.items():
                headers.setdefault(header, value)
        if self.auth:
            headers.update(self.auth)

        kwargs["headers"] = headers
        kwargs["hooks"] = {"response": self.log}

        response = self.session.request(method=method, url=url, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None

    def get(self, path: str, params=None, **kwargs):
        kwargs.setdefault("allow_redirects", True)
        return self.request("get", path, params=params, **kwargs)

    def post(self, path: str, data=None, json=None, **kwargs):
        return self.request("post", path, data=data, json=json, **kwargs)

    def log(self, resp, *args, **kwargs):
        response_data = resp.json() if resp.content else None

        body = None
        if (
            resp.request.body
            and resp.request.headers["Content-Type"] == "application/json"
        ):
            body = json.loads(resp.request.body)
        elif (
            resp.request.body
            and "multipart/form-data" in resp.request.headers["Content-Type"]
        ):
            body = resp.request.body.decode("utf8")

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

    def operation(
        self,
        operation_id: str,
        path,
        data: dict,
        method="POST",
        request_kwargs: Optional[dict] = None,
    ) -> Union[List[Object], Object]:
        assert path, "Relative path to API root needs to be supplied."
        return self.request(
            method,
            path,
            operation=operation_id,
            json=data,
            request_kwargs=request_kwargs,
        )
