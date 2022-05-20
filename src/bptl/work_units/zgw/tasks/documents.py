import logging
from typing import Dict, List
from urllib.parse import urlparse
from uuid import UUID

from zds_client.schema import get_operation_url
from zgw_consumers.concurrent import parallel
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
    Set the ``indicatieGebruiksrecht`` to ``false`` of all INFORMATIEOBJECTen related to the ZAAK.
    The INFORMATIEOBJECTen in ZAAKINFORMATIEOBJECTen must point to INFORMATIEOBJECTen in an API that complies with the Documenten API 1.0.x
      (https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/index).

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

    * ``zaakUrl``: full URL of the ZAAK

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.

    * ``services``: DEPRECATED - support will be removed in 1.1

    **Sets no process variables**
    """

    def get_zaak_informatieobjecten(self, zaak_url: str) -> List[str]:
        zrc_client = self.get_client(APITypes.zrc)
        zaak_informatieobjecten = zrc_client.list(
            "zaakinformatieobject", query_params={"zaak": zaak_url}
        )
        return zaak_informatieobjecten

    def lock_document(self, document_url: str) -> dict:
        drc_client = self.get_drc_client(document_url)
        response = drc_client.operation(
            operation_id="enkelvoudiginformatieobject_lock",
            uuid=get_document_uuid(document_url),
            data={},
        )
        return {
            "url": document_url,
            "data": {"indicatieGebruiksrecht": False, "lock": response["lock"]},
        }

    def update_document(self, data: dict):
        drc_client = self.get_drc_client(data["url"])

        # Set indication
        drc_client.partial_update("enkelvoudiginformatieobject", **data)

    def unlock_document(self, data: dict):
        # zds_client doesnt allow setting expected_status on zds_client.client.Client.operation.
        # The drc returns a 204 on an unlock operation, the zds_client expects a 200.
        # For now use the logic from zds_client.client.Client.operation but add expected_status.
        drc_client = self.get_drc_client(data["url"])
        url = get_operation_url(
            drc_client.schema,
            operation="enkelvoudiginformatieobject_unlock",
            base_url=drc_client.base_url,
            uuid=get_document_uuid(data["url"]),
        )
        drc_client.request(
            url,
            operation="enkelvoudiginformatieobject_unlock",
            method="POST",
            json={"lock": data["data"]["lock"]},
            expected_status=204,
        )

    def perform(self) -> dict:
        variables = self.task.get_variables()

        # Retrieve io url
        zaak_url = check_variable(variables, "zaakUrl")
        zaak_informatieobjecten = self.get_zaak_informatieobjecten(zaak_url)
        zios = [zio["informatieobject"] for zio in zaak_informatieobjecten]

        # lock io and set data
        with parallel() as executor:
            responses = list(executor.map(self.lock_document, zios))

        # update io
        with parallel() as executor:
            list(executor.map(self.update_document, responses))

        # unlock io
        with parallel() as executor:
            list(executor.map(self.unlock_document, responses))

        return {}
