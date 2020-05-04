from concurrent import futures
from typing import Dict
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from zgw_consumers.constants import APITypes

from bptl.tasks.base import check_variable
from bptl.tasks.registry import register

from ..nlx import get_nlx_headers
from ..utils import get_paginated_results
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


@register
class CreateEigenschap(ZGWWorkUnit):
    """
    Set a particular EIGENSCHAP value for a given zaak.

    Unique eigenschappen can be defined for a given zaaktype. This task looks up the
    eigenschap reference for the given zaak and will set the provided value.

    **Required process variables**

    * ``zaakUrl``: URL reference to a ZAAK in a Zaken API. The eigenschap is created
      for this zaak.
    * ``eigenschap``: a JSON Object containing the name and value:

      .. code-block:: json

        {
            "naam": "eigenschapnaam as in zaaktypecatalogus",
            "value": "<value to set>"
        }


    * ``services``: JSON Object of connection details for ZGW services:

      .. code-block:: json

        {
            "<ztc alias>": {"jwt": "Bearer <JWT value>"}
            "<zrc alias>": {"jwt": "Bearer <JWT value>"}
        }

    **Optional process variables**

    * ``NLXProcessId``: a process id for purpose registration ("doelbinding")
    * ``NLXSubjectIdentifier``: a subject identifier for purpose registration ("doelbinding")

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion

    **Sets no process variables**
    """

    # TODO: validate formaat eigenschap as declared by ZTC

    def perform(self) -> dict:
        # prep clients
        ztc_client = self.get_client(APITypes.ztc)
        zrc_client = self.get_client(APITypes.zrc)

        # get vars
        variables = self.task.get_variables()

        zaak_url = check_variable(variables, "zaakUrl")
        zaak_uuid = zaak_url.split("/")[-1]
        eigenschap = check_variable(variables, "eigenschap", empty_allowed=True)
        if not eigenschap:
            return {}

        naam = check_variable(eigenschap, "naam")
        waarde = check_variable(eigenschap, "waarde")

        # fetch zaaktype - either from process variable or derive from zaak
        zaaktype = variables.get("zaaktype")
        if zaaktype is None or not isinstance(zaaktype, str):
            zaak = zrc_client.retrieve("zaak", uuid=zaak_uuid)
            zaaktype = zaak["zaaktype"]

        # fetch eigenschappen
        eigenschappen = get_paginated_results(
            ztc_client, "eigenschap", query_params={"zaaktype": zaaktype}
        )
        eigenschap_url = next(
            (
                eigenschap["url"]
                for eigenschap in eigenschappen
                if eigenschap["naam"] == naam
            )
        )

        zrc_client.create(
            "zaakeigenschap",
            {"zaak": zaak_url, "eigenschap": eigenschap_url, "waarde": waarde,},
            zaak_uuid=zaak_uuid,
            request_kwargs={"headers": get_nlx_headers(variables)},
        )

        return {}


@register
class RelateerZaak(ZGWWorkUnit):
    """
    Relate a zaak to another zaak.

    Different kinds of relations are possible, specifying the relation type will ensure
    this is done correctly. Existing relations are not affected - if there are any, they
    are retained and the new relation is added.

    **Required process variables**

    * ``hoofdZaakUrl``: URL reference to a ZAAK in a Zaken API. This zaak receives the
      relations.
    * ``zaakUrl``: URL reference to another ZAAK in a Zaken API, to be related
      to ``zaakUrl``.
    * ``bijdrageAard``: the type of relation. One of ``vervolg``, ``onderwerp`` or
      ``bijdrage``.
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

    def perform(self) -> dict:
        # prep clients
        zrc_client = self.get_client(APITypes.zrc)

        # get vars
        variables = self.task.get_variables()

        zaak_url = check_variable(variables, "hoofdZaakUrl")
        bijdrage_zaak_url = check_variable(variables, "zaakUrl")
        bijdrage_aard = check_variable(variables, "bijdrageAard")

        if bijdrage_aard not in ["vervolg", "onderwerp", "bijdrage"]:
            raise ValueError(f"Unknown 'bijdrage_aard': '{bijdrage_aard}'")

        headers = get_nlx_headers(variables)

        zaak = zrc_client.retrieve("zaak", url=zaak_url, request_headers=headers)

        relevante_andere_zaken = zaak["relevanteAndereZaken"]
        relevante_andere_zaken.append(
            {"url": bijdrage_zaak_url, "aardRelatie": bijdrage_aard,}
        )

        zrc_client.partial_update(
            "zaak",
            {"relevanteAndereZaken": relevante_andere_zaken},
            url=zaak_url,
            request_headers=headers,
        )

        return {}


@register
class CreateZaakObject(ZGWWorkUnit):
    """
    Create a new ZAAKOBJECT for the ZAAK in the process.

    **Required process variables**

    * ``zaakUrl``: full URL of the ZAAK to create a new ZaakObject for
    * ``objectUrl``: full URL of the OBJECT to set
    * ``objectType``: type of the OBJECT
    * ``services``: JSON Object of connection details for ZGW services:

        .. code-block:: json

          {
              "<zrc alias>": {"jwt": "Bearer <JWT value>"},
          }

    **Optional process variables**

    * ``objectTypeOverige``: description of the OBJECT type if objectType = 'overige'
    * ``relatieomschrijving``: description of relationship between ZAAK and OBJECT

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion

    **Sets the process variables**

    * ``zaakobject``: the full URL of the created ZAAKOBJECT
    """

    def create_zaakobject(self) -> dict:
        variables = self.task.get_variables()
        zrc_client = self.get_client(APITypes.zrc)
        data = {
            "zaak": variables["zaakUrl"],
            "object": variables["objectUrl"],
            "objectType": variables["objectType"],
            "objectTypeOverige": variables.get("objectTypeOverige", ""),
            "relatieomschrijving": variables.get("relatieomschrijving", ""),
        }
        zaakobject = zrc_client.create("zaakobject", data)
        return zaakobject

    def perform(self):
        zaakobject = self.create_zaakobject()
        return {"zaakObjectUrl": zaakobject["url"]}
