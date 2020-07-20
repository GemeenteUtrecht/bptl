import logging
from datetime import date
from typing import Any, Dict, Optional

from django.utils import timezone

from zgw_consumers.constants import APITypes

from bptl.tasks.registry import register

from ..nlx import get_nlx_headers
from .base import ZGWWorkUnit
from .resultaat import CreateResultaatTask

logger = logging.getLogger(__name__)


@register
class CreateZaakTask(ZGWWorkUnit):
    """
    Create a ZAAK in the configured Zaken API and set the initial status.

    The initial status is the STATUSTYPE with ``volgnummer`` equal to 1 for the
    ZAAKTYPE.

    By default, the ``registratiedatum`` and ``startdatum`` are set to todays date.

    **Required process variables**

    * ``zaaktype``: the full URL of the ZAAKTYPE
    * ``organisatieRSIN``: RSIN of the organisation
    * ``services``: JSON Object of connection details for ZGW services:

        .. code-block:: json

          {
              "<zrc alias>": {"jwt": "Bearer <JWT value>"},
              "<ztc alias>": {"jwt": "Bearer <JWT value>"}
          }

    **Optional process variables**

    * ``NLXProcessId``: a process id for purpose registration ("doelbinding")
    * ``NLXSubjectIdentifier``: a subject identifier for purpose registration ("doelbinding")
    * ``zaakDetails``: a JSON object with extra properties for zaak creation. See
      https://zaken-api.vng.cloud/api/v1/schema/#operation/zaak_create for the available
      properties. Note that you can use these to override ``zaaktype``, ``bronorganisatie``,
      ``verantwoordelijkeOrganisatie``, ``registratiedatum`` and ``startdatum`` if you'd
      require so.
    * ``initialStatusRemarks``: a text to use for the remarks field on the initial status.
      Must be maximum 1000 characters.
    * ``initiator``: a JSON object with data used to create a rol for a particular zaak. See
        https://zaken-api.vng.cloud/api/v1/schema/#operation/rol_create for the properties available.

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion

    **Sets the process variables**

    * ``zaak``: the JSON response of the created ZAAK
    * ``zaakUrl``: the full URL of the created ZAAK
    * ``zaakIdentificatie``: the identificatie of the created ZAAK
    """

    def create_zaak(self) -> dict:
        variables = self.task.get_variables()

        extra_props = variables.get("zaakDetails", {})

        client_zrc = self.get_client(APITypes.zrc)
        today = date.today().strftime("%Y-%m-%d")
        data = {
            "zaaktype": variables["zaaktype"],
            "bronorganisatie": variables["organisatieRSIN"],
            "verantwoordelijkeOrganisatie": variables["organisatieRSIN"],
            "registratiedatum": today,
            "startdatum": today,
            **extra_props,
        }

        headers = get_nlx_headers(variables)
        zaak = client_zrc.create("zaak", data, request_kwargs={"headers": headers})
        return zaak

    def create_rol(self, zaak: dict) -> Optional[dict]:
        variables = self.task.get_variables()
        initiator = variables.get("initiator", {})

        if not initiator:
            return None

        ztc_client = self.get_client(APITypes.ztc)
        query_params = {
            "zaaktype": variables["zaaktype"],
            "omschrijvingGeneriek": initiator.get("omschrijvingGeneriek", "initiator"),
        }
        rol_typen = ztc_client.list("roltype", query_params)
        if not rol_typen:
            logger.info(
                "Roltype specified, but no matching roltype found in the zaaktype.",
                extra={"query_params": query_params},
            )
            return None

        zrc_client = self.get_client(APITypes.zrc)
        request_body = {
            "zaak": zaak["url"],
            "betrokkene": initiator.get("betrokkene", ""),
            "betrokkeneType": initiator.get("betrokkeneType", "natuurlijk_persoon"),
            "roltype": rol_typen["results"][0]["url"],
            "roltoelichting": initiator.get("roltoelichting", ""),
            "indicatieMachtiging": initiator.get("indicatieMachtiging", ""),
            "betrokkeneIdentificatie": initiator.get("betrokkeneIdentificatie", {}),
        }
        rol = zrc_client.create("rol", request_body,)
        return rol

    def create_status(self, zaak: dict) -> dict:
        variables = self.task.get_variables()

        # get statustype for initial status
        ztc_client = self.get_client(APITypes.ztc)
        statustypen = ztc_client.list(
            "statustype", {"zaaktype": variables["zaaktype"]}
        )["results"]
        statustype = next(filter(lambda x: x["volgnummer"] == 1, statustypen))

        initial_status_remarks = variables.get("initialStatusRemarks", "")

        # create status
        zrc_client = self.get_client(APITypes.zrc)
        data = {
            "zaak": zaak["url"],
            "statustype": statustype["url"],
            "datumStatusGezet": timezone.now().isoformat(),
            "statustoelichting": initial_status_remarks,
        }
        status = zrc_client.create("status", data)
        return status

    def perform(self) -> Dict[str, Any]:
        zaak = self.create_zaak()
        self.create_status(zaak)
        self.create_rol(zaak)

        return {
            "zaak": zaak,
            "zaakUrl": zaak["url"],
            "zaakIdentificatie": zaak["identificatie"],
        }


@register
class CloseZaakTask(ZGWWorkUnit):
    """
    Close the ZAAK by setting the final STATUS.

    A ZAAK is required to have a RESULTAAT.

    **Required process variables**

    * ``zaakUrl``: full URL of the ZAAK
    * ``services``: JSON Object of connection details for ZGW services:

        .. code-block:: json

          {
              "<zrc alias>": {"jwt": "Bearer <JWT value>"},
              "<ztc alias>": {"jwt": "Bearer <JWT value>"}
          }

    **Optional process variables**

    * ``resultaattype``: full URL of the RESULTAATTYPE to set.
      If provided the RESULTAAT is created before the ZAAK is closed

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion

    **Sets the process variables**

    * ``einddatum``: date of closing the zaak
    * ``archiefnominatie``: shows if the zaak should be destroyed or stored permanently
    * ``archiefactiedatum``: date when the archived zaak should be destroyed or transferred to the archive
    """

    def create_resultaat(self):
        resultaattype = self.task.get_variables().get("resultaattype")

        if not resultaattype:
            return

        create_resultaat_work_unit = CreateResultaatTask(self.task)
        create_resultaat_work_unit.create_resultaat()

    def close_zaak(self) -> dict:
        variables = self.task.get_variables()

        # build clients
        zrc_client = self.get_client(APITypes.zrc)
        ztc_client = self.get_client(APITypes.ztc)

        # get statustype to close zaak
        zaak_url = variables.get("zaakUrl", variables.get("zaak"))
        zaaktype = zrc_client.retrieve("zaak", url=zaak_url)["zaaktype"]
        statustypen = ztc_client.list("statustype", {"zaaktype": zaaktype})["results"]
        statustype = next(filter(lambda x: x["isEindstatus"] is True, statustypen))

        # create status to close zaak
        data = {
            "zaak": zaak_url,
            "statustype": statustype["url"],
            "datumStatusGezet": timezone.now().isoformat(),
        }
        zrc_client.create("status", data)

        # get zaak to receive calculated variables
        zaak_closed = zrc_client.retrieve("zaak", url=zaak_url)
        return zaak_closed

    def perform(self):
        self.create_resultaat()
        resultaat = self.close_zaak()

        return {
            "einddatum": resultaat["einddatum"],
            "archiefnominatie": resultaat["archiefnominatie"],
            "archiefactiedatum": resultaat["archiefactiedatum"],
        }
