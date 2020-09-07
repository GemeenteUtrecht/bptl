import logging
from typing import Dict
from urllib.parse import urlparse
from uuid import UUID

from zgw_consumers.constants import APITypes

from bptl.tasks.base import check_variable
from bptl.tasks.registry import register

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


@register
class LockDocument(ZGWWorkUnit):
    """
    Lock a Documenten API document.

    A locked document cannot be mutated without having the lock ID.

    **Required process variables**

    * ``informatieobject``: String, API URL of the document to lock.
      The API must comply with the Documenten API 1.0.x
      (https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/index).

    * ``services``: JSON Object of connection details for ZGW service:

        .. code-block:: json

          {
              "<drc alias>": {"jwt": "Bearer <JWT value>"},
          }

    **Sets the process variables**

    * ``lockId``: String, Lock ID for the locked document. Required to unlock or mutate
      the document.
    """

    def perform(self) -> Dict[str, str]:
        variables = self.task.get_variables()

        # Retrieve document
        document_url = check_variable(variables, "informatieobject")
        drc_client = self.get_client(APITypes.drc)

        # Lock document
        response = drc_client.operation(
            operation_id="enkelvoudiginformatieobject_lock",
            uuid=get_document_uuid(document_url),
            data={},
        )

        return {"lockId": response["lock"]}


@register
class UnlockDocument(ZGWWorkUnit):
    """
    Unlock a Documenten API document.

    **Required process variables**

    * ``informatieobject``: String, API URL of the document to lock.
      The API must comply with the Documenten API 1.0.x
      (https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/index).

    * ``lockId``: String, Lock ID for the locked DRC document, obtained from locking the
      document.

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
        document_url = check_variable(variables, "informatieobject")
        lock_id = check_variable(variables, "lockId")
        drc_client = self.get_client(APITypes.drc)

        # Unock document
        drc_client.operation(
            operation_id="enkelvoudiginformatieobject_unlock",
            uuid=get_document_uuid(document_url),
            data={"lock": lock_id},
        )

        return {}
