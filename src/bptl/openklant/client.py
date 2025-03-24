from typing import Optional

from zds_client.client import Client

from .models import OpenKlantConfig


def get_openklant_client(openklant_config: Optional[OpenKlantConfig] = None) -> Client:
    openklant_config = (
        OpenKlantConfig.get_solo() if not openklant_config else openklant_config
    )

    client = openklant_config.build_client()
    client.operation_suffix_mapping = {
        "list": "List",
        "retrieve": "Read",
        "create": "Create",
        "update": "Update",
        "partial_update": "PartialUpdate",
        "delete": "Delete",
    }
    return client
