from django.core.mail import get_connection

from bptl.openklant.mail_backend import KCCEmailBackend, KCCEmailConfig


def get_kcc_email_connection() -> KCCEmailBackend:
    # TODO: Wow dirty.
    config = KCCEmailConfig.get_solo()
    backend = KCCEmailBackend(
        host=config.host,
        port=config.port,
        username=config.username,
        password=(
            config.password
            if config.password
            else settings.KCC_EMAIL_HOST_PASSWORD or settings.EMAIL_HOST_PASSWORD
        ),
        use_tls=config.use_tls,
        use_ssl=config.use_ssl,
        timeout=config.timeout,
    )
    return backend
