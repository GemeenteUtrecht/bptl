import logging
import warnings
from concurrent import futures
from typing import Dict, Optional
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from zgw_consumers.api_models.constants import AardRelatieChoices
from zgw_consumers.constants import APITypes

from bptl.tasks.base import MissingVariable, check_variable
from bptl.tasks.registry import register

from ..nlx import get_nlx_headers
from ..utils import get_paginated_results
from .base import ZGWWorkUnit, require_zrc, require_ztc

logger = logging.getLogger(__name__)


@register
@require_zrc
class RelateDocumentToZaakTask(ZGWWorkUnit):
    """
    Create relations between ZAAK and INFORMATIEOBJECT

    **Required process variables**

    * ``zaakUrl`` [str]: URL-reference to the ZAAK.
    * ``informatieobject`` [str]: URL-reference to the INFORMATIEOBJECT. If empty, no relation
      will be created.
    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl`` [str]: send an empty POST request to this URL to signal completion.

    **Sets the process variables**

    * ``zaakinformatieobject`` [str]: URL-reference to ZAAKINFORMATIEOBJECT.
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
@require_zrc
class RelatePand(ZGWWorkUnit):
    """
    Relate Pand objects from the BAG to a ZAAK as ZAAKOBJECTs.

    One or more PANDen are related to the ZAAK in the process as ZAAKOBJECT.

    **Required process variables**

    * ``zaakUrl`` [str]: URL-reference to a ZAAK in a Zaken API. The PANDen are related to this.
    * ``panden`` [list[str]]: URL-references to PANDen in BAG API.
    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.

    **Optional process variables**

    * ``NLXProcessId`` [str]: a process id for purpose registration ("doelbinding").
    * ``NLXSubjectIdentifier`` [str]: a subject identifier for purpose registration ("doelbinding").

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl`` [str]: send an empty POST request to this URL to signal completion

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
        warnings.warn(
            "The `RelatedPand` task is deprected in favour of `CreateZaakObject`. "
            "It will be removed in 1.0.",
            DeprecationWarning,
        )
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
@require_zrc
@require_ztc
class CreateEigenschap(ZGWWorkUnit):
    """
    Set a particular EIGENSCHAP value for a given zaak.

    Unique eigenschappen can be defined for a given zaaktype. This task looks up the
    eigenschap reference for the given zaak and will set the provided value.

    **Required process variables**

    * ``zaakUrl`` [str]: URL-reference to a ZAAK in a Zaken API. The eigenschap is created
      for this zaak.
    * ``eigenschap`` [json]: a JSON Object containing the name and value:

      .. code-block:: json

            {
                "naam": "eigenschapnaam as in zaaktypecatalogus",
                "waarde": "<value to set>"
            }

    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.

    **Optional process variables**

    * ``NLXProcessId`` [str]: a process id for purpose registration ("doelbinding")
    * ``NLXSubjectIdentifier`` [str]: a subject identifier for purpose registration ("doelbinding")

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl`` [str]: send an empty POST request to this URL to signal completion

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
        waarde = check_variable(eigenschap, "waarde", empty_allowed=True)
        if not waarde:
            return {}

        # fetch zaaktype - either from process variable or derive from zaak
        zaaktype = variables.get("zaaktype")
        if zaaktype is None or not isinstance(zaaktype, str):
            zaak = zrc_client.retrieve("zaak", uuid=zaak_uuid)
            zaaktype = zaak["zaaktype"]

        # fetch eigenschappen
        eigenschappen = get_paginated_results(
            ztc_client, "eigenschap", query_params={"zaaktype": zaaktype}
        )
        try:
            eigenschap_url = next(
                (
                    eigenschap["url"]
                    for eigenschap in eigenschappen
                    if eigenschap["naam"] == naam
                )
            )
        except StopIteration:
            # eigenschap not found - abort
            logger.info("Eigenschap '%s' did not exist on the zaaktype, aborting.")
            return {}

        zrc_client.create(
            "zaakeigenschap",
            {
                "zaak": zaak_url,
                "eigenschap": eigenschap_url,
                "waarde": waarde,
            },
            zaak_uuid=zaak_uuid,
            request_kwargs={"headers": get_nlx_headers(variables)},
        )

        return {}


@register
@require_zrc
class RelateerZaak(ZGWWorkUnit):
    """
    Relate a zaak to another zaak.

    Different kinds of relations are possible, specifying the relation type will ensure
    this is done correctly. Existing relations are not affected - if there are any, they
    are retained and the new relation is added.

    **Required process variables**

    * ``hoofdZaakUrl`` [str]: URL-reference to a ZAAK in a Zaken API. This zaak receives the
      relations.
    * ``zaakUrl`` [str]: URL-reference to another ZAAK in a Zaken API, to be related
      to ``zaakUrl``.
    * ``bijdrageAard`` [str]: the type of relation. One of ``vervolg``, ``onderwerp`` or
      ``bijdrage``.
    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.

    **Optional process variables**

    * ``NLXProcessId`` [str]: a process id for purpose registration ("doelbinding").
    * ``NLXSubjectIdentifier`` [str]: a subject identifier for purpose registration ("doelbinding").
    * ``bijdrageAardOmgekeerdeRichting`` [str]: the type of reverse relation. One of ``vervolg``, ``onderwerp``, ``bijdrage`` or empty (``""``).
      Default is ``onderwerp`` if the process variable isn't given.

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl`` [str]: send an empty POST request to this URL to signal completion.

    **Sets no process variables**
    """

    def perform(self) -> Optional[dict]:
        # prep clients
        zrc_client = self.get_client(APITypes.zrc)

        # get vars
        variables = self.task.get_variables()

        zaak_url = variables.get("hoofdZaakUrl")
        if not zaak_url:
            logger.info("No 'hoofdZaakUrl' provided, skipping task execution.")
            return

        bijdrage_zaak_url = check_variable(variables, "zaakUrl")
        bijdrage_aard = check_variable(variables, "bijdrageAard")

        if bijdrage_aard not in AardRelatieChoices.values:
            raise ValueError(f"Unknown 'bijdrage_aard': '{bijdrage_aard}'")

        headers = get_nlx_headers(variables)

        zaak = zrc_client.retrieve("zaak", url=zaak_url, request_headers=headers)

        relevante_andere_zaken = zaak["relevanteAndereZaken"]
        relevante_andere_zaken.append(
            {
                "url": bijdrage_zaak_url,
                "aardRelatie": bijdrage_aard,
            }
        )

        zrc_client.partial_update(
            "zaak",
            {"relevanteAndereZaken": relevante_andere_zaken},
            url=zaak_url,
            request_headers=headers,
        )

        try:
            bijdrage_aard_omgekeerde_richting = check_variable(
                variables, "bijdrageAardOmgekeerdeRichting", empty_allowed=True
            )
            if (
                bijdrage_aard_omgekeerde_richting
                and bijdrage_aard_omgekeerde_richting not in AardRelatieChoices.values
            ):
                raise ValueError(
                    f"Unknown 'bijdrageAardOmgekeerdeRichting': '{bijdrage_aard_omgekeerde_richting}'"
                )
        except MissingVariable:
            # To avoid having to edit BPMN models - default of bijdrage_aard_omgekeerde_richting
            # is "onderwerp" if it isn't explicitly given in the variables.
            bijdrage_aard_omgekeerde_richting = AardRelatieChoices.onderwerp

        # Relating of secondary zaken to their main zaak.
        if (
            bijdrage_aard != AardRelatieChoices.onderwerp
            and bijdrage_aard_omgekeerde_richting
        ):
            bijdrage_zaak = zrc_client.retrieve(
                "zaak", url=bijdrage_zaak_url, request_headers=headers
            )
            relevante_andere_zaken_bijdrage_zaak = bijdrage_zaak["relevanteAndereZaken"]
            relevante_andere_zaken_bijdrage_zaak.append(
                {
                    "url": zaak_url,
                    "aardRelatie": bijdrage_aard_omgekeerde_richting,
                }
            )
            zrc_client.partial_update(
                "zaak",
                {"relevanteAndereZaken": relevante_andere_zaken_bijdrage_zaak},
                url=bijdrage_zaak_url,
                request_headers=headers,
            )

        return {}


@register
@require_zrc
class CreateZaakObject(ZGWWorkUnit):
    """
    Create a new ZAAKOBJECT for the ZAAK in the process.

    **Required process variables**

    * ``zaakUrl`` [str]: URL-reference to the ZAAK to create a new ZaakObject for.
    * ``objectUrl`` [str]: URL-reference to the OBJECT to set.
    * ``objectType`` [str]: Description of OBJECT [i.e., adres, besluit, etc].
    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.

    If ``zaakUrl`` is not given - returns empty dictionary.

    **Optional process variables**

    * ``objectTypeOverige`` [str]: description of the OBJECT type if objectType == 'overige'.
    * ``relatieomschrijving`` [str]: description of relationship between ZAAK and OBJECT.

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl`` [str]: send an empty POST request to this URL to signal completion.

    **Sets the process variables**

    * ``zaakObjectUrl`` [str]: URL-reference to the created ZAAKOBJECT.
    """

    def create_zaakobject(self, variables: dict) -> dict:
        zrc_client = self.get_client(APITypes.zrc)
        data = {
            "zaak": check_variable(variables, "zaakUrl"),
            "object": check_variable(variables, "objectUrl"),
            "objectType": check_variable(variables, "objectType"),
            "objectTypeOverige": variables.get("objectTypeOverige", ""),
            "relatieomschrijving": variables.get("relatieomschrijving", ""),
        }
        zaakobject = zrc_client.create("zaakobject", data)
        return zaakobject

    def perform(self) -> dict:
        variables = self.task.get_variables()
        if variables.get("zaakUrl", ""):
            zaakobject = self.create_zaakobject(variables)
            return {"zaakObjectUrl": zaakobject["url"]}
        else:
            logger.info("Case url is not given, aborting.")
            return {}
