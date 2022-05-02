import warnings

from django.utils.translation import gettext_lazy as _

from zgw_consumers.constants import APITypes

from bptl.credentials.api import get_credentials
from bptl.tasks.base import WorkUnit
from bptl.tasks.models import DefaultService
from bptl.tasks.registry import register

from ..client import MultipleServices, NoAuth, NoService

PROCESS_VAR_NAME = "bptlAppId"


require_zrc = register.require_service(
    APITypes.zrc, description=_("The Zaken API to use.")
)
require_ztc = register.require_service(
    APITypes.ztc, description=_("The Catalogi API to use.")
)
require_drc = register.require_service(
    APITypes.drc, description=_("The Documenten API to use.")
)
require_brc = register.require_service(
    APITypes.brc, description=_("The Besluiten API to use.")
)


class ZGWWorkUnit(WorkUnit):
    def get_client(self, service_type: str):
        """
        create ZGW client with requested parameters
        """
        task_variables = self.task.get_variables()
        topic_name = self.task.topic_name
        default_services = DefaultService.objects.filter(
            task_mapping__topic_name=topic_name, service__api_type=service_type
        ).select_related("service")

        if not default_services:
            raise NoService(
                f"No {service_type} service is configured for topic '{topic_name}'"
            )
        if len(default_services) > 1:
            raise MultipleServices(
                f"Multiple '{service_type}' services configured for topic '{topic_name}'"
            )

        service = default_services[0].service

        client = service.build_client()
        client._log.task = self.task

        if PROCESS_VAR_NAME not in task_variables:
            raise NoService("Could not determine service credentials.")

        app_id = task_variables[PROCESS_VAR_NAME]
        auth_headers = get_credentials(app_id, service)[service]
        if auth_headers:
            client.set_auth_value(auth_headers)

        return client
