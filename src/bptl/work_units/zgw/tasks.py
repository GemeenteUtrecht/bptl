from datetime import date
from typing import Any, Dict

from django.utils import timezone

from zgw_consumers.constants import APITypes

from bptl.tasks.registry import register

from .base import ZGWWorkUnit
from .nlx import get_nlx_headers

__all__ = (
    "CreateZaakTask",
    "CreateStatusTask",
    "CreateResultaatTask",
    "RelateDocumentToZaakTask",
    "CloseZaakTask",
)


@register
class CreateZaakTask(ZGWWorkUnit):
    """
    Create a ZAAK in the configured Zaken API and set the initial status.

    The initial status is the STATUSTYPE with ``volgnummer`` equal to 1 for the
    ZAAKTYPE.

    **Required process variables**

    * ``zaaktype``: the full URL of the ZAAKTYPE
    * ``organisatieRSIN``: RSIN of the organisation
    * ``services``: JSON Object of connection details for ZGW services:
        * "<ZRC service name>": {"jwt": value for Authorization header in the api}
        * "<ZTC service name>": {"jwt": value for Authorization header in the api}

    **Optional process variables**

    * ``NLXProcessId``: a process id for purpose registration ("doelbinding")
    * ``NLXSubjectIdentifier``: a subject identifier for purpose registration ("doelbinding")

    **Sets the process variables**

    * ``zaak``: the JSON response of the created ZAAK
    * ``zaakUrl``: the full URL of the created ZAAK
    * ``zaakIdentificatie``: the identificatie of the created ZAAK
    """

    def create_zaak(self) -> dict:
        variables = self.task.get_variables()

        client_zrc = self.get_client(APITypes.zrc)
        today = date.today().strftime("%Y-%m-%d")
        data = {
            "zaaktype": variables["zaaktype"],
            "vertrouwelijkheidaanduiding": "openbaar",
            "bronorganisatie": variables["organisatieRSIN"],
            "verantwoordelijkeOrganisatie": variables["organisatieRSIN"],
            "registratiedatum": today,
            "startdatum": today,
        }

        headers = get_nlx_headers(variables)
        zaak = client_zrc.create("zaak", data, request_kwargs={"headers": headers})
        return zaak

    def create_status(self, zaak: dict) -> dict:
        variables = self.task.get_variables()

        # get statustype for initial status
        ztc_client = self.get_client(APITypes.ztc)
        statustypen = ztc_client.list(
            "statustype", {"zaaktype": variables["zaaktype"]}
        )["results"]
        statustype = next(filter(lambda x: x["volgnummer"] == 1, statustypen))

        # create status
        zrc_client = self.get_client(APITypes.zrc)
        data = {
            "zaak": zaak["url"],
            "statustype": statustype["url"],
            "datumStatusGezet": timezone.now().isoformat(),
        }
        status = zrc_client.create("status", data)
        return status

    def perform(self) -> Dict[str, Any]:
        zaak = self.create_zaak()
        self.create_status(zaak)
        return {
            "zaak": zaak,
            "zaakUrl": zaak["url"],
            "zaakIdentificatie": zaak["identificatie"],
        }


@register
class CreateStatusTask(ZGWWorkUnit):
    """
    Create a new STATUS for the ZAAK in the process.

    Required process variables:

    * **zaak**: full URL of the ZAAK to create a new status for
    * **statustype**: full URL of the STATUSTYPE to set
    * **services**: JSON Object of connection details for ZGW services:
        * "<ZRC service name>": {"jwt": value for Authorization header in the api}
        * "<ZTC service name>": {"jwt": value for Authorization header in the api}

    The task sets the process variables:

    * **status**: the full URL of the created STATUS
    """

    def create_status(self) -> dict:
        variables = self.task.get_variables()
        zrc_client = self.get_client(APITypes.zrc)
        data = {
            "zaak": variables["zaak"],
            "statustype": variables["statustype"],
            "datumStatusGezet": timezone.now().isoformat(),
        }
        status = zrc_client.create("status", data)
        return status

    def perform(self):
        status = self.create_status()
        return {"status": status["url"]}


@register
class CreateResultaatTask(ZGWWorkUnit):
    """
    Set the RESULTAAT for the ZAAK in the process.

    A resultaat is required to be able to close a zaak. A zaak can only have one
    resultaat.

    Required process variables:

    * **zaak**: full URL of the ZAAK to set the RESULTAAT for
    * **resultaattype**: full URL of the RESULTAATTYPE to set
    * **services**: JSON Object of connection details for ZGW services:
        * "<ZRC service name>": {"jwt": value for Authorization header in the api}

    Optional process variables:

    * **toelichting**

    The task sets the process variables:

    * **resultaat**: the full URL of the created RESULTAAT
    """

    def create_resultaat(self):
        zrc_client = self.get_client(APITypes.zrc)
        data = {
            "zaak": self.task.get_variables()["zaak"],
            "resultaattype": self.task.get_variables()["resultaattype"],
            "toelichting": self.task.get_variables().get("toelichting", ""),
        }

        resultaat = zrc_client.create("resultaat", data)
        return resultaat

    def perform(self):
        resultaat = self.create_resultaat()
        return {"resultaat": resultaat["url"]}


@register
class RelateDocumentToZaakTask(ZGWWorkUnit):
    """
    Create relations between ZAAK and INFORMATIEOBJECT

    Required process variables:

    * **zaak**: full URL of the ZAAK
    * **informatieobject**: full URL of the INFORMATIEOBJECT
    * **services**: JSON Object of connection details for ZGW services:
        * "<ZRC service name>": {"jwt": value for Authorization header in the api}

    The task sets the process variables:

    * **zaakinformatieobject**: full URL of ZAAKINFORMATIEOBJECT
    """

    def relate_document(self) -> dict:
        zrc_client = self.get_client(APITypes.zrc)
        data = {
            "zaak": self.task.get_variables()["zaak"],
            "informatieobject": self.task.get_variables()["informatieobject"],
        }
        zio = zrc_client.create("zaakinformatieobject", data)
        return zio

    def perform(self):
        resultaat = self.relate_document()
        return {"zaakinformatieobject": resultaat["url"]}


@register
class CloseZaakTask(ZGWWorkUnit):
    """
    Close the ZAAK by setting the final STATUS.

    A ZAAK is required to have a RESULTAAT.

    Required process variables:

    * **zaak**: full URL of the ZAAK
    * **services**: JSON Object of connection details for ZGW services:
        * "<ZRC service name>": {"jwt": value for Authorization header in the api}
        * "<ZTC service name>": {"jwt": value for Authorization header in the api}

    The task sets the process variables:

    * **einddatum**: date of closing the zaak
    * **archiefnominatie**: shows if the zaak should be destroyed or stored permanently
    * **archiefactiedatum**: date when the archived zaak should be destroyed or transferred to the archive
    """

    def close_zaak(self) -> dict:
        # build clients
        zrc_client = self.get_client(APITypes.zrc)
        ztc_client = self.get_client(APITypes.ztc)

        # get statustype to close zaak
        zaak = self.task.get_variables()["zaak"]
        zaaktype = zrc_client.retrieve("zaak", zaak)["zaaktype"]
        statustypen = ztc_client.list("statustype", {"zaaktype": zaaktype})["results"]
        statustype = next(filter(lambda x: x["isEindstatus"] is True, statustypen))

        # create status to close zaak
        data = {
            "zaak": zaak,
            "statustype": statustype,
            "datumStatusGezet": timezone.now().isoformat(),
        }
        zrc_client.create("status", data)

        # get zaak to receive calculated variables
        zaak_closed = zrc_client.retrieve("zaak", zaak)
        return zaak_closed

    def perform(self):
        resultaat = self.close_zaak()

        return {
            "einddatum": resultaat["einddatum"],
            "archiefnominatie": resultaat["archiefnominatie"],
            "archiefactiedatum": resultaat["archiefactiedatum"],
        }


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

    **Sets no process variables**
    """

    def perform(self) -> dict:
        # prep client
        zrc_client = self.get_client(APITypes.zrc)

        # get vars
        variables = self.task.get_variables()
        zaak_url = variables["zaakUrl"]
        pand_urls = variables["panden"]

        # See https://zaken-api.vng.cloud/api/v1/schema/#operation/zaakobject_create
        bodies = [
            {
                "zaak": zaak_url,
                "object": pand_url,
                "objectType": "pand",
                "relatieomschrijving": "",  # TODO -> process var?
            }
            for pand_url in pand_urls
        ]

        headers = get_nlx_headers(variables)

        # TODO: concurrent.futures this
        for body in bodies:
            zrc_client.create("zaakobject", body, request_kwargs={"headers": headers})

        return {}
