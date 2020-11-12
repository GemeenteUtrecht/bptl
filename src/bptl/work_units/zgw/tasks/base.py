import warnings

from bptl.credentials.api import get_credentials
from bptl.tasks.base import WorkUnit
from bptl.work_units.zgw.models import DefaultService

from ..client import MultipleServices, NoAuth, NoService

PROCESS_VAR_NAME = "bptlAppId"


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

        if PROCESS_VAR_NAME not in task_variables and "services" not in task_variables:
            raise NoService("Could not determine service credentials.")

        if PROCESS_VAR_NAME in task_variables:
            app_id = task_variables[PROCESS_VAR_NAME]
            auth_headers = get_credentials(app_id, service)[service]
            if auth_headers:
                client.set_auth_value(auth_headers)

        # fall back on the old behaviour
        else:
            warnings.warn(
                "The 'services' credentials variable is deprecated. Please migrate "
                f"as soon as possible to the new {PROCESS_VAR_NAME} application identifier "
                "variable",
                DeprecationWarning,
            )
            services_vars = task_variables["services"]
            alias = default_services[0].alias
            jwt = services_vars.get(alias, {}).get("jwt")
            if not jwt:
                raise NoAuth(f"Expected 'jwt' key for service with alias '{alias}'")
            client.set_auth_value({"Authorization": jwt})

        return client
