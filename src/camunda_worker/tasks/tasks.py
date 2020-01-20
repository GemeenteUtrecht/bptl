from datetime import date

from django.utils import timezone

from zgw_consumers.models import APITypes, Service

from camunda_worker.external_tasks.constants import Statuses
from camunda_worker.external_tasks.models import FetchedTask

from .registry import register


class Task:
    def __init__(self, task: FetchedTask):
        self.task = task

    def perform(self) -> dict:
        raise NotImplementedError("subclasses of Task must provide a perform() method")

    def save_result(self, result_data: dict):
        self.task.status = Statuses.completed
        self.task.result_variables = result_data
        self.task.save()


@register
class CreateZaakTask(Task):
    """
    This task creates zaak in ZRC API and sets initial status for this zaak

    Required process variables:
    * zaaktype
    * organisatieRSIN
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

        zaak = client.create("zaak", data)
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
class CreateStatusTask(Task):
    """
    This task creates new status for particular zaak in ZRC API

    Required process variables:
    * zaak
    * statustype
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
class CreateResultaatTask(Task):
    """
        This task creates new resultaat for particular zaak in ZRC API

        Required process variables:
        * zaak
        * resultaattype

        Optional process variables:
        * toelichting
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
