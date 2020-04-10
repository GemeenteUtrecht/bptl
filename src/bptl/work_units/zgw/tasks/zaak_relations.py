from concurrent import futures
from typing import Dict
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from zgw_consumers.constants import APITypes

from bptl.tasks.base import check_variable
from bptl.tasks.registry import register

from ..nlx import get_nlx_headers
from .base import ZGWWorkUnit


@register
class RelateDocumentToZaakTask(ZGWWorkUnit):
    """
    Create relations between ZAAK and INFORMATIEOBJECT

    **Required process variables**

    * ``zaakUrl``: full URL of the ZAAK
    * ``informatieobject``: full URL of the INFORMATIEOBJECT. If empty, no relation
       will be created.
    * ``services``: JSON Object of connection details for ZGW services:

        .. code-block:: json

          {
              "<zrc alias>": {"jwt": "Bearer <JWT value>"},
          }

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion

    **Sets the process variables**

    * ``zaakinformatieobject``: full URL of ZAAKINFORMATIEOBJECT
    """

    def relate_document(self) -> dict:
        variables = self.task.get_variables()

        informatieobject = check_variable(
            variables, "informatieobject", empty_allowed=True
        )
        if not informatieobject:
            return None

        # recently renamed zaak -> zaakUrl: handle correctly
        zaak = variables.get("zaakUrl", variables.get("zaak"))

        zrc_client = self.get_client(APITypes.zrc)
        data = {"zaak": zaak, "informatieobject": informatieobject}
        zio = zrc_client.create("zaakinformatieobject", data)
        return zio

    def perform(self) -> Dict[str, str]:
        zio = self.relate_document()
        if zio is None:
            return {}
        return {"zaakinformatieobject": zio["url"]}


@register
class RelatePand(ZGWWorkUnit):
    """
    Relate Pand objects from the BAG to a ZAAK as ZAAKOBJECTs.

    One or more PANDen are related to the ZAAK in the process as ZAAKOBJECT.

    **Required process variables**

    * ``zaakUrl``: URL reference to a ZAAK in a Zaken API. The PANDen are related to this.
    * ``panden``: list of URL references to PANDen in BAG API.
    * ``services``: JSON Object of connection details for ZGW services:

      .. code-block:: json

        {
            "<zrc alias>": {"jwt": "Bearer <JWT value>"}
        }

    **Optional process variables**

    * ``NLXProcessId``: a process id for purpose registration ("doelbinding")
    * ``NLXSubjectIdentifier``: a subject identifier for purpose registration ("doelbinding")

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion

    **Sets no process variables**
    """

    @staticmethod
    def _clean_url(url: str) -> str:
        scheme, netloc, path, query, fragment = urlsplit(url)
        query_dict = parse_qs(query)

        # Delete the geldigOp querystring, which contains the date the pand was retrieved.
        # It's still the same pand, but might a different representation on another date.
        # Dropping the QS allows the zaakobject list filter to work when passing in the
        # object to find related zaken.
        if "geldigOp" in query_dict:
            del query_dict["geldigOp"]

        query = urlencode(query_dict, doseq=True)
        return urlunsplit((scheme, netloc, path, query, fragment))

    def perform(self) -> dict:
        # prep client
        zrc_client = self.get_client(APITypes.zrc)

        # get vars
        variables = self.task.get_variables()

        zaak_url = check_variable(variables, "zaakUrl")
        pand_urls = check_variable(variables, "panden", empty_allowed=True)

        # See https://zaken-api.vng.cloud/api/v1/schema/#operation/zaakobject_create
        bodies = [
            {
                "zaak": zaak_url,
                "object": self._clean_url(pand_url),
                "objectType": "pand",
                "relatieomschrijving": "",  # TODO -> process var?
            }
            for pand_url in pand_urls
        ]

        headers = get_nlx_headers(variables)

        def _api_call(body):
            zrc_client.create("zaakobject", body, request_kwargs={"headers": headers})

        with futures.ThreadPoolExecutor() as executor:
            executor.map(_api_call, bodies)

        return {}


class CreateEigenschap(ZGWWorkUnit):
    # TODO: validate formaat eigenschap as declared by ZTC
    pass
