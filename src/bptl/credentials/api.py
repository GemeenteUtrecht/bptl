from typing import Dict

from zgw_consumers.models import Service

from .models import AppServiceCredentials


def get_auth_headers(app_id: str, service: Service) -> Dict[str, str]:
    credentials = AppServiceCredentials.objects.select_related("service").get(
        app__app_id=app_id, service=service
    )
    import bpdb

    bpdb.set_trace()


def get_credentials(app_id: str, *services: Service) -> Dict[Service, Dict[str, str]]:
    import bpdb

    bpdb.set_trace()
