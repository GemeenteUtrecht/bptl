from ..authentication import WebhookAuthentication
from .models import XentialConfiguration


class XentialAuthentication(WebhookAuthentication):

    config_class = XentialConfiguration
    application_name = "Xential API"
