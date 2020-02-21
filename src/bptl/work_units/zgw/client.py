from typing import Any

from zds_client.client import Client


class ZGWClient(Client):
    auth_value = None

    def set_auth_value(self, auth_value):
        self.auth_value = auth_value

    def pre_request(self, method: str, url: str, **kwargs) -> Any:
        """
        Add authorization header to requests
        """
        if self.auth_value:
            headers = kwargs.get("headers", {})
            headers["Authorization"] = self.auth_value

        return super().pre_request(method, url, **kwargs)
