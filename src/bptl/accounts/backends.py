import logging
from copy import deepcopy
from typing import Any, List

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password

from glom import assign, glom
from mozilla_django_oidc_db.backends import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)


def obfuscate_claims(claims: dict, claims_to_obfuscate: List[str]) -> dict:
    copied_claims = deepcopy(claims)
    logger.info(copied_claims)
    for claim_name in claims_to_obfuscate:
        logger.info(f"obfuscating claim: {claim_name}")
        # NOTE: this does not support claim names that have dots in them
        claim_value = glom(copied_claims, claim_name)
        assign(copied_claims, claim_name, obfuscate_claim_value(claim_value))
    return copied_claims


class LoggingBackendMozilla(OIDCAuthenticationBackend):
    def verify_claims(self, claims) -> bool:
        logger.info(claims)
        claims_to_obfuscate = super().get_sensitive_claims_names()
        claims_to_obfuscate_str = f"claims to obfuscate: {claims_to_obfuscate}"
        logger.info(claims_to_obfuscate_str)
        id_field = getattr(self.config, self.config_identifier_field)
        config_identifier_field_str = f"config_identifier_field: {id_field}"
        logger.info(config_identifier_field_str)
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
