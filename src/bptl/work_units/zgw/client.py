from typing import Any

from django.conf import settings
from django.utils.module_loading import import_string

from zds_client.client import Client


def get_client_class() -> type:
    client_class = getattr(
        settings, "ZGW_CLIENT_CLASS", "bptl.work_units.zgw.client.ZGWClient"
    )
    Client = import_string(client_class)
    return Client


class ZGWClient(Client):
    auth_value = None

    def pre_request(self, method: str, url: str, **kwargs) -> Any:
        """
        Add authorization header to requests
        """
        if self.auth_value:
            headers = kwargs.get("headers", {})
            headers["Authorization"] = self.auth_value

        return super().pre_request(method, url, **kwargs)
