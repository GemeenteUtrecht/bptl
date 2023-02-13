import logging
from datetime import date
from typing import Any, Dict, Optional

from django.utils import timezone

from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import RolOmschrijving
from zgw_consumers.constants import APITypes

from bptl.tasks.base import MissingVariable, check_variable
from bptl.tasks.registry import register

from ..nlx import get_nlx_headers
from .base import ZGWWorkUnit, require_zrc, require_ztc
from .resultaat import CreateResultaatTask

logger = logging.getLogger(__name__)


@register
@require_zrc
@require_ztc
class CreateZaakTask(ZGWWorkUnit):
    """
    Create a ZAAK in the configured Zaken API and set the initial status.

    The initial status is the STATUSTYPE with ``volgnummer`` equal to 1 for the
    ZAAKTYPE.

    By default, the ``registratiedatum`` and ``startdatum`` are set to todays date.

    **Required process variables**

    * ``organisatieRSIN`` [str]: RSIN of the organisation.
    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.
    * ``catalogusDomein`` [str]: abbrevation for the domain of the catalogus of the ZAAKTYPEn.
    * ``zaaktypeIdentificatie``: ID of ZAAKTYPE.

    **Optional process variables**

    * ``NLXProcessId`` [str]: a process id for purpose registration ("doelbinding").
    * ``NLXSubjectIdentifier`` [str]: a subject identifier for purpose registration ("doelbinding").
    * ``initialStatusRemarks`` [str]: a text to use for the remarks field on the initial status.
      Must be maximum 1000 characters.
    * ``catalogusRSIN`` [str]: RSIN of catalogus where zaaktype can be found. Defaults to ``organisatieRSIN``.
    * ``initiator`` [str]: a JSON object with data used to create a rol for a particular zaak. See
      https://zaken-api.vng.cloud/api/v1/schema/#operation/rol_create for the properties available.
    * ``zaakDetails`` [json]: a JSON object with extra properties for zaak creation. See
      https://zaken-api.vng.cloud/api/v1/schema/#operation/zaak_create for the available
      properties. Note that you can use these to override ``zaaktype``, ``bronorganisatie``,
      ``verantwoordelijkeOrganisatie``, ``registratiedatum`` and ``startdatum`` if you'd
      require so.
    * ``zaaktype`` [str]: URL-reference to the ZAAKTYPE.

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl`` [str]: send an empty POST request to this URL to signal completion.

    **Sets the process variables**

    * ``zaak`` [json]: the JSON response of the created ZAAK.
    * ``zaakUrl`` [str]: URL-reference to the created ZAAK.
    * ``zaakIdentificatie`` [str]: the identificatie of the created ZAAK.
    """

    def _get_zaaktype(self, variables: dict) -> str:
        if not hasattr(self, "_zaaktype"):
            if not (zaaktype_url := variables.get("zaaktype", "")):
                catalogus_domein = check_variable(variables, "catalogusDomein")
                catalogus_rsin = variables.get("catalogusRSIN") or check_variable(
                    variables, "organisatieRSIN"
                )
                zaaktype_identificatie = check_variable(
                    variables, "zaaktypeIdentificatie"
                )

                request_kwargs = {
                    "params": {"domein": catalogus_domein, "rsin": catalogus_rsin}
                }
                client_ztc = self.get_client(APITypes.ztc)
                catalogus = client_ztc.list("catalogus", request_kwargs=request_kwargs)
                try:
                    catalogus_url = catalogus["results"][0]["url"]
                except (KeyError, IndexError):
                    raise ValueError(
                        "No catalogus found with domein %s and RSIN %s."
                        % (catalogus_domein, catalogus_rsin)
                    )

                request_kwargs = {
                    "params": {
                        "catalogus": catalogus_url,
                        "identificatie": zaaktype_identificatie,
                    }
                }
                zaaktypen = client_ztc.list("zaaktype", request_kwargs=request_kwargs)
                if zaaktypen["count"] == 0:
                    raise ValueError(
                        "No zaaktype was found with catalogus %s and identificatie %s."
                        % (
                            catalogus_url,
                            zaaktype_identificatie,
                        )
                    )

                zaaktypen = [
                    factory(ZaakType, zaaktype) for zaaktype in zaaktypen["results"]
                ]

                def _filter_on_geldigheid(zaaktype: ZaakType) -> bool:
                    if zaaktype.einde_geldigheid:
                        return (
                            zaaktype.begin_geldigheid
                            <= date.today()
                            <= zaaktype.einde_geldigheid
                        )
                    else:
                        return zaaktype.begin_geldigheid <= date.today()

                zaaktypen = [zt for zt in zaaktypen if _filter_on_geldigheid(zt)]
                # Use the ZT with none as einde geldigheid or einde geldigheid that's further into the future
                # in the edge case that einde geldigheid old zaaktype is today and a new zaaktype is geldig from today.
                if len(zaaktypen) > 1:
                    zaaktypen_without_einde_geldigheid = [
                        zt for zt in zaaktypen if not zt.einde_geldigheid
                    ]

                    # If this does not exist -> get one with einde_geldigheid most distant into the future
                    if len(zaaktypen_without_einde_geldigheid) == 0:
                        max_einde_geldigheid = max(
                            [zt.einde_geldigheid for zt in zaaktypen]
                        )
                        zaaktypen = [
                            zt
                            for zt in zaaktypen
                            if zt.einde_geldigheid == max_einde_geldigheid
                        ]
                    else:
                        zaaktypen = zaaktypen_without_einde_geldigheid

                if len(zaaktypen) != 1:
                    raise ValueError(
                        "No%s zaaktype was found with catalogus %s, identificatie %s with begin_geldigheid <= %s <= einde_geldigheid."
                        % (
                            "" if len(zaaktypen) == 0 else " unique",
                            catalogus_url,
                            zaaktype_identificatie,
                            date.today(),
                        )
                    )

                zaaktype_url = zaaktypen[0].url

            self._zaaktype = zaaktype_url
        return self._zaaktype

    def create_zaak(self) -> dict:
        variables = self.task.get_variables()
        extra_props = variables.get("zaakDetails", {})
        zaaktype_url = self._get_zaaktype(variables)

        client_zrc = self.get_client(APITypes.zrc)
        today = date.today().strftime("%Y-%m-%d")
        data = {
            "zaaktype": zaaktype_url,
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
        initiator = variables.get("Hoofdbehandelaar", {})

        if not initiator:
            return None

        ztc_client = self.get_client(APITypes.ztc)
        query_params = {
            "zaaktype": self._get_zaaktype(variables),
            "omschrijvingGeneriek": initiator.get(
                "omschrijvingGeneriek", RolOmschrijving.initiator
            ),
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
        rol = zrc_client.create(
            "rol",
            request_body,
        )
        return rol

    def create_status(self, zaak: dict) -> dict:
        variables = self.task.get_variables()

        # get statustype for initial status
        ztc_client = self.get_client(APITypes.ztc)
        statustypen = ztc_client.list(
            "statustype", {"zaaktype": self._get_zaaktype(variables)}
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
            "zaakUrl": zaak["url"],
            "zaakIdentificatie": zaak["identificatie"],
        }


@register
@require_zrc
@require_ztc
class CloseZaakTask(ZGWWorkUnit):
    """
    Close the ZAAK by setting the final STATUS.

    A ZAAK is required to have a RESULTAAT.

    **Required process variables**

    * ``zaakUrl`` [str]: URL-reference to the ZAAK.
    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.

    **Optional process variables**

    * ``omschrijving`` [str]: description of the RESULTAATTYPE. RESULTAATTYPE takes priority.
    * ``resultaattype`` [str]: URL-reference to the RESULTAATTYPE to set.
    * ``statustoelichting`` [str]: description of the STATUS.
      If provided the RESULTAAT is created before the ZAAK is closed.

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl`` [str]: send an empty POST request to this URL to signal completion.

    **Sets the process variables**

    * ``einddatum`` [str]: date of closing the zaak.
    * ``archiefnominatie`` [str]: shows if the zaak should be destroyed or stored permanently.
    * ``archiefactiedatum`` [str]: date when the archived zaak should be destroyed or transferred to the archive.
    """

    def create_resultaat(self) -> None:
        try:
            create_resultaat_work_unit = CreateResultaatTask(self.task)
            create_resultaat_work_unit.create_resultaat()
        except MissingVariable:
            variables = self.task.get_variables()
            zaak_url = variables.get("zaakUrl", variables.get("zaak"))
            logger.warning("Can't create resultaat for %s." % zaak_url)
            return

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
        if toelichting := variables.get("statustoelichting"):
            data["statustoelichting"] = toelichting
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


@register
@require_zrc
class LookupZaak(ZGWWorkUnit):
    """
    Look up a single ZAAK by identificatie and bronorganisatie.

    This task looks up the referenced zaak, and if found sets the zaakUrl as a
    process variable. If not found, the variable will be empty.

    You can use this to check if the referenced ZAAK does indeed exist, and relate
    it to other objects.

    **Required process variables**

    * ``identificatie`` [str]: identification of the zaak, commonly known as "zaaknummer".
    * ``bronorganisatie`` [str]: RSIN of the source organization for the zaak. The combination
      of identificatie and bronorganisatie uniquely identifies a zaak.
    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl`` [str]: send an empty POST request to this URL to signal completion.

    **Sets the process variables**

    * ``zaakUrl`` [str]: URL-reference of the retrieved zaak, if retrieved at all. If the
      zaak was not found, the value will be ``Null``.
    """

    def perform(self) -> Dict[str, Optional[str]]:
        variables = self.task.get_variables()
        client_zrc = self.get_client(APITypes.zrc)

        identificatie = check_variable(variables, "identificatie")
        bronorganisatie = check_variable(variables, "bronorganisatie")

        zaken: dict = client_zrc.list(
            "zaak",
            {
                "bronorganisatie": bronorganisatie,
                "identificatie": identificatie,
            },
        )

        # paginated response
        if zaken["results"]:
            zaak_url = zaken["results"][0]["url"]
        else:
            zaak_url = None

        return {"zaakUrl": zaak_url}
