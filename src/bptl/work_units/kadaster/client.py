from typing import Dict
from urllib.parse import urljoin

import requests
from timeline_logger.models import TimelineLog
from zgw_consumers.models import Service


class BRTClient:
    task = None

    def __init__(self, service: Service, auth_header: Dict[str, str]):
        self.api_root = service.api_root
        self.auth = auth_header

    def post(self, path: str, *args, **kwargs):
        assert not path.startswith("/"), "Only relative paths are supported."
        url = urljoin(self.api_root, path)

        # add the API headers
        headers = kwargs.pop("headers", {})
        headers.update(self.auth)
        kwargs["headers"] = headers
        kwargs["hooks"] = {"response": self.log}

        response = requests.post(url, *args, **kwargs)
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
