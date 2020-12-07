"""
Provide base client implementations, based on requests.

Note that for the time being only get/post are implemented.
"""
from typing import Dict
from urllib.parse import urljoin

import requests
from timeline_logger.models import TimelineLog
from zgw_consumers.models import Service


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
