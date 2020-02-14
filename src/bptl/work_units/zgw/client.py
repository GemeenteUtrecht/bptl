from django.conf import settings
from django.utils.module_loading import import_string


def get_client_class() -> type:
    client_class = getattr(settings, "ZGW_CLIENT_CLASS", "zds_client.Client")
    Client = import_string(client_class)
    return Client
