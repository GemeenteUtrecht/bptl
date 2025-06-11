import threading

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
from django.db import models

from solo.models import SingletonModel


class KCCEmailConfig(SingletonModel):
    """
    Configuration for the KCC email backend.
    """

    class Meta:
        verbose_name = "KCC Email Configuration"

    def __str__(self):
        return "KCC Email Configuration"

    host = models.CharField(
        max_length=254, default="smtp.kcc.nl", blank=True, null=True
    )
    port = models.PositiveIntegerField(default=587)
    username = models.CharField(max_length=254, blank=True, null=True)
    password = models.CharField(max_length=254, blank=True, null=True)
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=True)
    timeout = models.PositiveIntegerField(default=10)
    from_email = models.CharField(max_length=254, blank=True, null=True)
    reply_to = models.CharField(max_length=254, blank=True, null=True)


class KCCEmailBackend(EmailBackend):
    """
    A wrapper that manages the SMTP network connection.
    """

    def __init__(
        self,
        host=None,
        port=None,
        username=None,
        password=None,
        use_tls=None,
        fail_silently=False,
        use_ssl=None,
        timeout=None,
        ssl_keyfile=None,
        ssl_certfile=None,
        **kwargs
    ):
        super().__init__(fail_silently=fail_silently)
        self.host = host or settings.KCC_EMAIL_HOST
        self.port = port or settings.KCC_EMAIL_PORT
        self.username = settings.KCC_EMAIL_HOST_USER if username is None else username
        self.password = (
            settings.KCC_EMAIL_HOST_PASSWORD if password is None else password
        )
        self.use_tls = settings.KCC_EMAIL_USE_TLS if use_tls is None else use_tls
        self.use_ssl = settings.KCC_EMAIL_USE_SSL if use_ssl is None else use_ssl
        self.timeout = settings.KCC_EMAIL_TIMEOUT if timeout is None else timeout
        if self.use_ssl and self.use_tls:
            raise ValueError(
                "EMAIL_USE_TLS/EMAIL_USE_SSL are mutually exclusive, so only set "
                "one of those settings to True."
            )
        self.connection = None
        self._lock = threading.RLock()
