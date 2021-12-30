import logging
from typing import Dict
from urllib.parse import urlparse
from uuid import UUID

from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from bptl.tasks.base import check_variable
from bptl.tasks.registry import register

from ..client import NoService
from .base import ZGWWorkUnit

logger = logging.getLogger(__name__)


def get_document_uuid(document_url: str) -> str:
    path = urlparse(document_url).path
    # EIO URLs end with the UUID
    _uuid = path.split("/")[-1]
    try:
        UUID(_uuid)
    except ValueError:
        raise ValueError("URL does not seem to end with a UUID (4).")
    return _uuid


class GetDRCMixin:
    """
    Temp workaround to get credentials for the relevant DRC.

    The services var should contain a DRC alias key with credentials, but that's
    currently a massive spaghetti. So, we'll allow for the time being that DRCs are
    all configured in BPTL, and we grab the right one from the document URL.
    """

    def get_drc_client(self, document_url: str) -> Service:
        try:
            return self.get_client(APITypes.drc)
        except NoService:
            client = Service.get_client(document_url)
            client._log.task = self.task
            return client


@register
class LockDocument(GetDRCMixin, ZGWWorkUnit):
    """
    Lock a Documenten API document.

    A locked document cannot be mutated without having the lock ID.

    **Required process variables**

    * ``informatieobject``: String, API URL of the document to lock.
      The API must comply with the Documenten API 1.0.x
      (https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/index).

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.

    * ``services``: DEPRECATED - support will be removed in 1.1

    **Sets the process variables**

    * ``lockId``: String, Lock ID for the locked document. Required to unlock or mutate
      the document.
    """

    def perform(self) -> Dict[str, str]:
        variables = self.task.get_variables()

        # Retrieve document
        document_url = check_variable(variables, "informatieobject")
        drc_client = self.get_drc_client(document_url)

        # Lock document
        response = drc_client.operation(
            operation_id="enkelvoudiginformatieobject_lock",
            uuid=get_document_uuid(document_url),
            data={},
        )

        return {"lockId": response["lock"]}


@register
class UnlockDocument(GetDRCMixin, ZGWWorkUnit):
    """
    Unlock a Documenten API document.

    **Required process variables**

    * ``informatieobject``: String, API URL of the document to lock.
      The API must comply with the Documenten API 1.0.x
      (https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/index).

    * ``lockId``: String, Lock ID for the locked DRC document, obtained from locking the
      document.

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.

    * ``services``: DEPRECATED - support will be removed in 1.1

    **Sets no process variables**
    """

    def perform(self) -> dict:
        variables = self.task.get_variables()

        # Retrieve document
        document_url = check_variable(variables, "informatieobject")
        lock_id = check_variable(variables, "lockId")
        drc_client = self.get_drc_client(document_url)

        # Unock document
        drc_client.operation(
            operation_id="enkelvoudiginformatieobject_unlock",
            uuid=get_document_uuid(document_url),
            data={"lock": lock_id},
        )

        return {}


@register
class SetIndicatieGebruiksrecht(GetDRCMixin, ZGWWorkUnit):
    """
    Set a document's ``indicatieGebruiksrecht`` to ``false``.

    From the API documentation:

        Indicatie of er beperkingen gelden aangaande het gebruik van het informatieobject
        anders dan raadpleging. Dit veld mag ``null`` zijn om aan te geven dat de
        indicatie nog niet bekend is. Als de indicatie gezet is, dan kan je de
        gebruiksrechten die van toepassing zijn raadplegen via de GEBRUIKSRECHTen
        resource.

        -- Documenten API documentation

    This task essentially switches the value from ``null`` to ``false``, implying re-use
    other than "consulting" is not allowed.

    **required process variables**

    * ``informatieobject``: String, API URL of the document to lock.
      The API must comply with the Documenten API 1.0.x
      (https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/index).

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.

    * ``services``: DEPRECATED - support will be removed in 1.1

    **Sets no process variables**
    """

    def perform(self) -> dict:
        variables = self.task.get_variables()

        # Retrieve document
        document_url = check_variable(variables, "informatieobject")
        drc_client = self.get_drc_client(document_url)

        # Set indication
        drc_client.partial_update(
            "enkelvoudiginformatieobject",
            data={"indicatieGebruiksrecht": False},
            url=document_url,
        )

        return {}
