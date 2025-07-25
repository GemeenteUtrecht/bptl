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
        from_email=None,
        **kwargs
    ):
        super().__init__(fail_silently=fail_silently)
        self.host = host or settings.KCC_EMAIL_HOST
        self.port = port or settings.KCC_EMAIL_PORT
        self.username = username or settings.KCC_EMAIL_HOST_USER
        self.password = password or settings.KCC_EMAIL_HOST_PASSWORD
        self.use_tls = use_tls or settings.KCC_EMAIL_USE_TLS
        self.use_ssl = use_ssl or settings.KCC_EMAIL_USE_SSL
        self.timeout = timeout or settings.KCC_EMAIL_TIMEOUT
        self.from_email = from_email or settings.KCC_DEFAULT_FROM_EMAIL
        if self.use_ssl and self.use_tls:
            raise ValueError(
                "EMAIL_USE_TLS/EMAIL_USE_SSL are mutually exclusive, so only set "
                "one of those settings to True."
            )
        self.connection = None
        self._lock = threading.RLock()
