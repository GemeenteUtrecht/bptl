from datetime import date

from django.utils import timezone

from zgw_consumers.models import APITypes, Service

from camunda_worker.external_tasks.models import FetchedTask

from .registry import register


class PerformTask:
    def __init__(self, task: FetchedTask):
        self.task = task

    def perform(self) -> dict:
        raise NotImplementedError(
            "subclasses of PerformTask must provide a perform() method"
        )

    def save_result(self, result_data: dict):
        self.task.result_variables = result_data
        self.task.save()


@register
class CreateZaakTask(PerformTask):
    """
    Create a ZAAK in the configured Zaken API and set the initial status.

    The initial status is the STATUSTYPE with ``volgnummer`` equal to 1 for the
    ZAAKTYPE.

    Required process variables:

    * zaaktype: the full URL of the ZAAKTYPE
    * organisatieRSIN: RSIN of the organisation

    Optional process variables:

    * NLXProcessId - a process id for purpose registration ("doelbinding")
    * NLXSubjectIdentifier - a subject identifier for purpose registration ("doelbinding")

    The task sets the process variables:

    * zaak: the full URL of the created ZAAK
    """

    def create_zaak(self) -> dict:
        zrc = Service.objects.get(api_type=APITypes.zrc)
        client = zrc.build_client()
        variables = self.task.flat_variables
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

        zaak = client.create("zaak", data, request_kwargs={"headers": headers})
        return zaak

    def create_status(self, zaak: dict) -> dict:
        # get statustype for initial status
        ztc = Service.objects.get(api_type=APITypes.ztc)
        ztc_client = ztc.build_client()
        statustypen = ztc_client.list(
            "statustype", {"zaaktype": self.task.flat_variables["zaaktype"]}
        )["results"]
        statustype = next(filter(lambda x: x["volgnummer"] == 1, statustypen))

        # create status
        zrc = Service.objects.get(api_type=APITypes.zrc)
        zrc_client = zrc.build_client()
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

        # save result
        result_data = {"zaak": zaak["url"]}
        self.save_result(result_data)
        return result_data


@register
class CreateStatusTask(PerformTask):
    """
    Create a new STATUS for the ZAAK in the process.

    Required process variables:

    * zaak: full URL of the ZAAK to create a new status for
    * statustype: full URL of the STATUSTYPE to set

    The task sets the process variables:

    * status: the full URL of the created STATUS
    """

    def create_status(self) -> dict:
        zrc = Service.objects.get(api_type=APITypes.zrc)
        zrc_client = zrc.build_client()
        data = {
            "zaak": self.task.flat_variables["zaak"],
            "statustype": self.task.flat_variables["statustype"],
            "datumStatusGezet": timezone.now().isoformat(),
        }
        status = zrc_client.create("status", data)
        return status

    def perform(self):
        status = self.create_status()

        # save result
        result_data = {"status": status["url"]}
        self.save_result(result_data)
        return result_data


@register
class CreateResultaatTask(PerformTask):
    """
    Set the RESULTAAT for the ZAAK in the process.

    A resultaat is required to be able to close a zaak. A zaak can only have one
    resultaat.

    Required process variables:

    * zaak: full URL of the ZAAK to set the RESULTAAT for
    * resultaattype: full URL of the RESULTAATTYPE to set

    Optional process variables:

    * toelichting

    The task sets the process variables:

    * resultaat: the full URL of the created RESULTAAT
    """

    def create_resultaat(self):
        zrc = Service.objects.get(api_type=APITypes.zrc)
        zrc_client = zrc.build_client()
        data = {
            "zaak": self.task.flat_variables["zaak"],
            "resultaattype": self.task.flat_variables["resultaattype"],
            "toelichting": self.task.flat_variables.get("toelichting", ""),
        }

        resultaat = zrc_client.create("resultaat", data)
        return resultaat

    def perform(self):
        resultaat = self.create_resultaat()

        result_data = {"resultaat": resultaat["url"]}
        self.save_result(result_data)
        return result_data


@register
class RelateDocumentToZaakTask(PerformTask):
    """
    Create relations between ZAAK and INFORMATIEOBJECT

    Required process variables:

    * zaak: full URL of the ZAAK
    * informatieobject: full URL of the INFORMATIEOBJECT

    The task sets the process variables:

    * zaakinformatieobject: full URL of ZAAKINFORMATIEOBJECT
    """

    def relate_document(self) -> dict:
        zrc = Service.objects.get(api_type=APITypes.zrc)
        zrc_client = zrc.build_client()
        data = {
            "zaak": self.task.flat_variables["zaak"],
            "informatieobject": self.task.flat_variables["informatieobject"],
        }
        zio = zrc_client.create("zaakinformatieobject", data)
        return zio

    def perform(self):
        resultaat = self.relate_document()

        result_data = {
            "zaakinformatieobject": resultaat["url"],
        }
        self.save_result(result_data)
        return result_data


@register
class CloseZaakTask(PerformTask):
    """
    Close the ZAAK by setting the final STATUS.

    A ZAAK is required to have a RESULTAAT.

    Required process variables:

    * zaak: full URL of the ZAAK

    The task sets the process variables:

    * einddatum: date of closing the zaak
    * archiefnominatie: shows if the zaak should be destroyed or stored permanently
    * archiefactiedatum: date when the archived zaak should be destroyed or transferred to the archive
    """

    def close_zaak(self) -> dict:
        # build clients
        zrc = Service.objects.get(api_type=APITypes.zrc)
        zrc_client = zrc.build_client()
        ztc = Service.objects.get(api_type=APITypes.ztc)
        ztc_client = ztc.build_client()

        # get statustype to close zaak
        zaak = self.task.flat_variables["zaak"]
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

        result_data = {
            "einddatum": resultaat["einddatum"],
            "archiefnominatie": resultaat["archiefnominatie"],
            "archiefactiedatum": resultaat["archiefactiedatum"],
        }

        self.save_result(result_data)
        return result_data
