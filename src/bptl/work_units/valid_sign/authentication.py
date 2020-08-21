from django.utils.crypto import constant_time_compare
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.request import Request

from bptl.accounts.models import User


class ValidSignAuthentication(BaseAuthentication):

    # Bulk taken from rest_framework.authentication.BasicAuthentication

    @staticmethod
    def _get_auth_key() -> str:
        # TODO: look up configured key in database
        return "some-random-key"

    def authenticate(self, request: Request):
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != b"basic":
            return None

        if len(auth) == 1:
            msg = _("Invalid basic header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _(
                "Invalid basic header. Credentials string should not contain spaces."
            )
            raise exceptions.AuthenticationFailed(msg)

        # extract the key from the header
        key = auth[1].decode()

        if not constant_time_compare(key, self._get_auth_key()):
            return None

        # User does not actually exist in the database!
        user = User(username="ValidSign API")
        return (user, None)
