import logging
from typing import Optional

from zgw_consumers.constants import APITypes

from bptl.tasks.base import check_variable
from bptl.tasks.registry import register

from .base import ZGWWorkUnit

logger = logging.getLogger(__name__)


@register
class CreateRolTask(ZGWWorkUnit):
    """
    Create a new ROL for the ZAAK in the process.

    **Required process variables**

    * ``zaakUrl``: full URL of the ZAAK to create a new rol for
    * ``omschrijving``: roltype.omschrijving for the ROL
    * ``betrokkene``: JSON object with data used to create a rol for a particular zaak. See
        https://zaken-api.vng.cloud/api/v1/schema/#operation/rol_create for the properties available.
    * ``services``: JSON Object of connection details for ZGW services:

        .. code-block:: json

          {
              "<zrc alias>": {"jwt": "Bearer <JWT value>"},
              "<ztc alias>": {"jwt": "Bearer <JWT value>"}
          }

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion

    **Sets the process variables**

    * ``rolUrl``: the full URL of the created ROL
    """

    def create_rol(self) -> dict:
        variables = self.task.get_variables()
        betrokkene = check_variable(variables, "betrokkene")
        omschrijving = check_variable(variables, "omschrijving")

        zrc_client = self.get_client(APITypes.zrc)
        zaak_url = check_variable(variables, "zaakUrl")
        zaak = zrc_client.retrieve("zaak", url=zaak_url)

        ztc_client = self.get_client(APITypes.ztc)
        query_params = {
            "zaaktype": zaak["zaaktype"],
        }
        rol_typen = ztc_client.list("roltype", query_params)
        rol_typen = [
            rol_type
            for rol_type in rol_typen["results"]
            if rol_type["omschrijving"] == omschrijving
        ]
        if not rol_typen:
            raise ValueError(
                f"No matching roltype with zaaktype = {zaak['zaaktype']} and omschrijving = {omschrijving} is found"
            )

        zrc_client = self.get_client(APITypes.zrc)
        data = {
            "zaak": zaak["url"],
            "betrokkene": betrokkene.get("betrokkene", ""),
            "betrokkeneType": betrokkene["betrokkeneType"],
            "roltype": rol_typen[0]["url"],
            "roltoelichting": betrokkene["roltoelichting"],
            "indicatieMachtiging": betrokkene.get("indicatieMachtiging", ""),
            "betrokkeneIdentificatie": betrokkene.get("betrokkeneIdentificatie", {}),
        }
        rol = zrc_client.create("rol", data,)
        return rol

    def perform(self):
        rol = self.create_rol()
        return {"rolUrl": rol["url"]}
