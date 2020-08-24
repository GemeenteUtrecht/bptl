from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.db.models.functions import Length

from zgw_consumers.client import ZGWClient
from zgw_consumers.constants import APITypes

from bptl.tasks.base import WorkUnit, check_variable
from bptl.tasks.models import TaskMapping
from bptl.tasks.registry import register


class NoService(Exception):
    pass


class NoAuth(Exception):
    pass


class DoesNotExist(Exception):
    pass


class DocumentTask(WorkUnit):
    def build_client(self, url: str) -> ZGWClient:
        default_services = TaskMapping.objects.get(
            topic_name=self.task.topic_name
        ).defaultservice_set.filter(service__api_type=APITypes.drc)

        if default_services.count() == 0:
            raise NoService(
                f"No {APITypes.drc} service is configured for topic {self.task.topic_name}"
            )

        services_vars = self.task.get_variables().get("services", {})
        if not services_vars and not settings.DEBUG:
            raise NoService(f"Expected service aliases in process variables")

        # Select the services that matches
        split_url = urlsplit(url)
        scheme_and_domain = urlunsplit(split_url[:2] + ("", "", ""))
        candidates = (
            default_services.filter(service__api_root__startswith=scheme_and_domain)
            .annotate(api_root_length=Length("service__api_root"))
            .order_by("-api_root_length")
        )

        for candidate in candidates.iterator():
            if url.startswith(candidate.service.api_root):
                service = candidate.service
                break
        else:
            raise DoesNotExist(f"No service found for url '{url}'")

        return service.build_client()

    def perform(self) -> dict:
        raise NotImplementedError


@register
class LockDocumentTask(DocumentTask):
    """Lock a DRC document.

    **Required process variables**

    * ``document``: str, API URL of a DRC document.
        The API must comply with the Documenten API 1.0.x (https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/index).

    * ``services``: JSON Object of connection details for ZGW service:

        .. code-block:: json

          {
              "<drc alias>": {"jwt": "Bearer <JWT value>"},
          }

    **Sets the process variables**

    * ``lockId``: str, Lock ID for the locked DRC document.
    """

    def perform(self) -> dict:
        variables = self.task.get_variables()

        # Retrieve document
        document_url = check_variable(variables, "document")
        drc_client = self.build_client(document_url)
        document_data = drc_client.retrieve(
            resource="enkelvoudiginformatieobject",
            url=document_url,
        )

        # Lock document
        response = drc_client.operation(
            operation_id="enkelvoudiginformatieobject_lock",
            uuid=document_data["uuid"],
            data={},
        )

        return {"lockId": response["lock"]}


@register
class UnlockDocumentTask(DocumentTask):
    """Unlock a DRC document.

    **Required process variables**

    * ``document``: str, API URL of a DRC document.
        The API must comply with the Documenten API 1.0.x (https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/index).

    * ``lockId``: str, Lock ID for the locked DRC document.

    * ``services``: JSON Object of connection details for ZGW services:

        .. code-block:: json

          {
              "<drc alias>": {"jwt": "Bearer <JWT value>"},
          }

    **Sets no process variables**
    """

    def perform(self) -> dict:
        variables = self.task.get_variables()

        # Retrieve document
        document_url = check_variable(variables, "document")
        lock_id = check_variable(variables, "lockId")
        drc_client = self.build_client(document_url)
        document_data = drc_client.retrieve(
            resource="enkelvoudiginformatieobject",
            url=document_url,
        )

        # Unock document
        drc_client.operation(
            operation_id="enkelvoudiginformatieobject_unlock",
            uuid=document_data["uuid"],
            data={"lock": lock_id},
        )

        return {}
