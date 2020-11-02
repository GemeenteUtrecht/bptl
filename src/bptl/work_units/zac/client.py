"""
Implements a ZAC client.
"""
from urllib.parse import urljoin

import requests

from .models import ZACConfig


class ZACClient:
    task = None

    def __init__(self, config=None):
        self.config = config or ZACConfig.get_solo()
        self.api_root = self.config.service.api_root
        self.auth = self.config.service.get_auth_header(self.api_root)

    def get(self, path: str, *args, **kwargs):
        url = urljoin(self.api_root, path)
        # add the API headers
        headers = kwargs.pop("headers", {})
        headers.update(self.auth)
        kwargs["headers"] = headers
        params = kwargs.get("params")

        response = requests.get(url, *args, **kwargs)
        response.raise_for_status()
        return response
