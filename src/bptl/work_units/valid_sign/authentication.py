from ..authentication import WebhookAuthentication
from .models import ValidSignConfiguration


class ValidSignAuthentication(WebhookAuthentication):
    config_class = ValidSignConfiguration
    application_name = "ValidSign API"
