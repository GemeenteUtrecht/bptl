import uuid
from datetime import date

from django.utils import timezone

from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .client import get_client_class

__all__ = (
    "CreateZaakTask",
    "CreateStatusTask",
    "CreateResultaatTask",
    "RelateDocumentToZaakTask",
    "CloseZaakTask",
)

Client = get_client_class()


class ZGWWorkUnit(WorkUnit):
    def build_client(self, configs):
        """
        create ZGW client with requested parameters
        """
        _uuid = uuid.uuid4()
        dummy_detail_url = f"{configs['apiRoot']}dummy/{_uuid}"
        Client = get_client_class()
        client = Client.from_url(dummy_detail_url)
        client.auth_value = configs["jwt"]
        return client


@register
class CreateZaakTask(ZGWWorkUnit):
    """
    Create a ZAAK in the configured Zaken API and set the initial status.

    The initial status is the STATUSTYPE with **volgnummer** equal to 1 for the
    ZAAKTYPE.

    Required process variables:

    * **zaaktype**: the full URL of the ZAAKTYPE
    * **organisatieRSIN**: RSIN of the organisation
    * **ZRC**: JSON Object of connection details for ZRC such as:
        * **apiRoot**: url to api root of ZRC
        * **jwt**: value for Authorization header in the api
    * **ZTC**: JSON Object of connection details for ZTC such as:
        * **apiRoot**: url to api root of ZTC
        * **jwt**: value for Authorization header in the api

    Optional process variables:

    * **NLXProcessId** - a process id for purpose registration ("doelbinding")
    * **NLXSubjectIdentifier** - a subject identifier for purpose registration ("doelbinding")

    The task sets the process variables:

    * **zaak**: the full URL of the created ZAAK
    """

    def create_zaak(self) -> dict:
        variables = self.task.get_variables()

        client_zrc = self.build_client(variables["ZRC"])
        today = date.today().strftime("%Y-%m-%d")
        data = {
            "zaaktype": variables["zaaktype"],
            "vertrouwelijkheidaanduiding": "openbaar",
            "bronorganisatie": variables["organisatieRSIN"],
            "verantwoordelijkeOrganisatie": variables["organisatieRSIN"],
            "registratiedatum": today,
            "startdatum": today,
        }

        headers = {}
        nlx_subject_identifier = variables.get("NLXSubjectIdentifier")
        if nlx_subject_identifier:
            headers["X-NLX-Request-Subject-Identifier"] = nlx_subject_identifier
        nlx_process_id = variables.get("NLXProcessId")
        if nlx_process_id:
            headers["X-NLX-Request-Process-Id"] = nlx_process_id

        zaak = client_zrc.create("zaak", data, request_kwargs={"headers": headers})
        return zaak

    def create_status(self, zaak: dict) -> dict:
        variables = self.task.get_variables()

        # get statustype for initial status
        ztc_client = self.build_client(variables["ZTC"])
        statustypen = ztc_client.list(
            "statustype", {"zaaktype": variables["zaaktype"]}
        )["results"]
        statustype = next(filter(lambda x: x["volgnummer"] == 1, statustypen))

        # create status
        zrc_client = self.build_client(variables["ZRC"])
        data = {
            "zaak": zaak["url"],
            "statustype": statustype["url"],
            "datumStatusGezet": timezone.now().isoformat(),
        }
        status = zrc_client.create("status", data)
        return status

    def perform(self):
        zaak = self.create_zaak()
        self.create_status(zaak)
        return {"zaak": zaak["url"]}


@register
class CreateStatusTask(ZGWWorkUnit):
    """
    Create a new STATUS for the ZAAK in the process.

    Required process variables:

    * **zaak**: full URL of the ZAAK to create a new status for
    * **statustype**: full URL of the STATUSTYPE to set
    * **ZRC**: JSON Object of connection details for ZRC such as:
        * **apiRoot**: url to api root of ZRC
        * **jwt**: value for Authorization header in the api

    The task sets the process variables:

    * **status**: the full URL of the created STATUS
    """

    def create_status(self) -> dict:
        variables = self.task.get_variables()
        zrc_client = self.build_client(variables["ZRC"])
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
    * **ZRC**: JSON Object of connection details for ZRC such as:
        * **apiRoot**: url to api root of ZRC
        * **jwt**: value for Authorization header in the api

    Optional process variables:

    * **toelichting**

    The task sets the process variables:

    * **resultaat**: the full URL of the created RESULTAAT
    """

    def create_resultaat(self):
        zrc_client = self.build_client(self.task.get_variables()["ZRC"])
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
    * **ZRC**: JSON Object of connection details for ZRC such as:
        * **apiRoot**: url to api root of ZRC
        * **jwt**: value for Authorization header in the api

    The task sets the process variables:

    * **zaakinformatieobject**: full URL of ZAAKINFORMATIEOBJECT
    """

    def relate_document(self) -> dict:
        zrc_client = self.build_client(self.task.get_variables()["ZRC"])
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
    * **ZRC**: JSON Object of connection details for ZRC such as:
        * **apiRoot**: url to api root of ZRC
        * **jwt**: value for Authorization header in the api
    * **ZTC**: JSON Object of connection details for ZTC such as:
        * **apiRoot**: url to api root of ZTC
        * **jwt**: value for Authorization header in the api

    The task sets the process variables:

    * **einddatum**: date of closing the zaak
    * **archiefnominatie**: shows if the zaak should be destroyed or stored permanently
    * **archiefactiedatum**: date when the archived zaak should be destroyed or transferred to the archive
    """

    def close_zaak(self) -> dict:
        # build clients
        zrc_client = self.build_client(self.task.get_variables()["ZRC"])
        ztc_client = self.build_client(self.task.get_variables()["ZTC"])

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
