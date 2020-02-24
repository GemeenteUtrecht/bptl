from typing import Any

from timeline_logger.models import TimelineLog
from zds_client.client import Client

from .log import DBLog


class NoService(Exception):
    pass


class MultipleServices(Exception):
    pass


class NoAuth(Exception):
    pass


class ZGWClient(Client):
    _log = DBLog()
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

    @property
    def log(self):
        """
        DB log entries.
        """
        return TimelineLog.objects.filter(extra_data__service_name=self.service)
