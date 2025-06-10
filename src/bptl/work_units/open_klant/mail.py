from django.core.mail import get_connection

from bptl.openklant.mail_backend import KCCEmailConfig


def get_kcc_email_connection():
    config = KCCEmailConfig.get_solo()
    backend = KCCEmailBackend(
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password,
        use_tls=config.use_tls,
        use_ssl=config.use_ssl,
        timeout=config.timeout,
    )
    return get_connection(backend)
