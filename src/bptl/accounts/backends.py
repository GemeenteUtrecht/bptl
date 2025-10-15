import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password

from mozilla_django_oidc_db.backends import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)


class LoggingBackendMozilla(OIDCAuthenticationBackend):
    def verify_claims(self, claims) -> bool:
        logger.info(claims)
        print(claims)
        return super().verify_claims(claims)


class UserModelEmailBackend(ModelBackend):
    """
    Authentication backend for login with email address.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = get_user_model().objects.get(email__iexact=username, is_active=True)
            if check_password(password, user.password):
                return user
        except get_user_model().DoesNotExist:
            # No user was found, return None - triggers default login failed
            return None
