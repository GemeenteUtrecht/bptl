from typing import Dict

from zgw_consumers.models import Service

from .models import AppServiceCredentials


def get_credentials(app_id: str, *services: Service) -> Dict[Service, Dict[str, str]]:
    credentials = AppServiceCredentials.objects.select_related("service").filter(
        app__app_id=app_id, service__in=services
    )
    explicit = {
        app_creds.service: app_creds.get_auth_headers() for app_creds in credentials
    }

    # explicit overrides defaults
    default = {
        service: service.build_client().auth_header
        for service in services
        if service not in explicit
    }
    return {**default, **explicit}
