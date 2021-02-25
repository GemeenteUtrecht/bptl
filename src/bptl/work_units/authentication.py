import logging
import re

from django.utils.crypto import constant_time_compare
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.request import Request

from bptl.accounts.models import User

logger = logging.getLogger(__name__)


HIDDEN_HEADERS = re.compile(
    "API|TOKEN|KEY|SECRET|PASS|SIGNATURE|AUTH", flags=re.IGNORECASE
)
CLEANSED_SUBSTITUTE = "********************"


def cleanse_header(header: str, value: str):
    if HIDDEN_HEADERS.search(header):
        return CLEANSED_SUBSTITUTE
    return value


class WebhookAuthentication(BaseAuthentication):

    config_class = None
    application_name = None

    # Bulk taken from rest_framework.authentication.BasicAuthentication

    def _get_auth_key(self) -> str:
        config = self.config_class.get_solo()
        return config.auth_key

    def authenticate(self, request: Request):
        self._log_headers(request)

        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != b"basic":
            logger.warning(
                "Did not receive basic auth header for request '%s'", request.path
            )
            return None

        if len(auth) == 1:
            msg = _("Invalid basic header. No credentials provided.")
            logger.warning(
                "Invalid basic auth for request '%s' (no creds)", request.path
            )
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _(
                "Invalid basic header. Credentials string should not contain spaces."
            )
            logger.warning(
                "Invalid basic auth for request '%s' (invalid header)", request.path
            )
            raise exceptions.AuthenticationFailed(msg)

        # extract the key from the header
        key = auth[1].decode()

        if not constant_time_compare(key, self._get_auth_key()):
            logger.warning("Invalid auth key used for request '%s'", request.path)
            return None

        # User does not actually exist in the database!
        user = User(username=self.application_name)
        return (user, None)

    @staticmethod
    def _log_headers(request: Request):
        cleansed = {
            header: cleanse_header(header, value)
            for header, value in request.headers.items()
        }
        logger.info(
            "Received request headers for request '%s': %r", request.path, cleansed
        )
