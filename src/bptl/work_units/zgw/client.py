from typing import Union

from timeline_logger.models import TimelineLog
from zgw_consumers.client import ZGWClient as _ZGWClient

from .log import DBLog


class NoService(Exception):
    pass


class MultipleServices(Exception):
    pass


class NoAuth(Exception):
    pass


class ZGWClient(_ZGWClient):
    _log = DBLog()

    def set_auth_value(self, auth_value: Union[str, dict]):
        self.auth = None

        if isinstance(auth_value, dict):
            self.auth_value = auth_value
        else:
            self.auth_value = {"Authorization": auth_value}

    @property
    def log(self):
        """
        DB log entries.
        """
        return TimelineLog.objects.filter(extra_data__service_name=self.service)
