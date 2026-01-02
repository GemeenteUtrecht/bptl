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
    # Generate auth headers from service configuration
    default = {}
    for service in services:
        if service not in explicit:
            client = service.build_client()
            # Extract auth header from the client's auth (ape_pie.APIClient)
            if hasattr(client, "auth") and client.auth:
                # For ZGW auth, we need to trigger token generation
                from requests import PreparedRequest

                req = PreparedRequest()
                req.headers = {}
                client.auth(req)
                default[service] = dict(req.headers)
            else:
                default[service] = {}
    return {**default, **explicit}
