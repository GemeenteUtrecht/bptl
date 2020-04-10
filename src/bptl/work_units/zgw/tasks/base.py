from django.conf import settings

from bptl.tasks.base import WorkUnit
from bptl.tasks.models import TaskMapping
from bptl.work_units.zgw.models import DefaultService

from ..client import MultipleServices, NoAuth, NoService


class ZGWWorkUnit(WorkUnit):
    def get_client(self, service_type: str):
        """
        create ZGW client with requested parameters
        """
        default_services = TaskMapping.objects.get(
            topic_name=self.task.topic_name
        ).defaultservice_set.filter(service__api_type=service_type)
        if default_services.count() == 0:
            raise NoService(
                f"No {service_type} service is configured for topic {self.task.topic_name}"
            )

        services_vars = self.task.get_variables().get("services", {})

        if not services_vars and not settings.DEBUG:
            raise NoService(f"Expected service aliases in process variables")

        aliases_vars = list(services_vars.keys())
        if aliases_vars:
            default_services = default_services.filter(alias__in=aliases_vars)

        try:
            default_service = default_services.get()
        except DefaultService.DoesNotExist:
            raise NoService(
                f"No {service_type} service with aliases {aliases_vars} is configured for topic {self.task.topic_name}"
            )
        except DefaultService.MultipleObjectsReturned:
            raise MultipleServices(
                f"More than one {service_type} service with aliases {aliases_vars} is "
                f"configured for topic {self.task.topic_name}"
            )

        client = default_service.service.build_client()
        client._log.task = self.task

        # add authorization header
        jwt = services_vars.get(default_service.alias, {}).get("jwt")
        if not jwt and not settings.DEBUG:
            raise NoAuth(
                f"Expected 'jwt' variable for {default_service.alias} in process variables"
            )

        client.set_auth_value(jwt)

        return client
