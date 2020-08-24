import logging

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
    * ``betrokkeneType``: type of the betrokkene
    * ``roltoelichting``: description of the ROL
    * ``betrokkene``: JSON object containing the data for ROL.betrokkeneIdentificatie. See
       https://zaken-api.vng.cloud/api/v1/schema/#operation/rol_create for the properties
       available.
    * ``services``: JSON Object of connection details for ZGW services:

        .. code-block:: json

          {
              "<zrc alias>": {"jwt": "Bearer <JWT value>"},
              "<ztc alias>": {"jwt": "Bearer <JWT value>"}
          }

    **Optional process variables**

    * ``indicatieMachtiging``: Authorization indication ("gemachtigde" or "machtiginggever")

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion

    **Sets the process variables**

    * ``rolUrl``: the full URL of the created ROL
    """

    def create_rol(self) -> dict:
        variables = self.task.get_variables()

        zrc_client = self.get_client(APITypes.zrc)
        zaak_url = check_variable(variables, "zaakUrl")
        zaak = zrc_client.retrieve("zaak", url=zaak_url)

        ztc_client = self.get_client(APITypes.ztc)
        query_params = {
            "zaaktype": zaak["zaaktype"],
            "omschrijvingGeneriek": check_variable(variables, "omschrijving"),
        }
        rol_typen = ztc_client.list("roltype", query_params)
        if not rol_typen:
            raise ValueError(
                f"No matching roltype with query {query_params} found in the zaaktype."
            )

        zrc_client = self.get_client(APITypes.zrc)
        data = {
            "zaak": zaak["url"],
            "betrokkeneType": check_variable(variables, "betrokkeneType"),
            "roltype": rol_typen["results"][0]["url"],
            "roltoelichting": check_variable(variables, "roltoelichting"),
            "indicatieMachtiging": variables.get("indicatieMachtiging", ""),
            "betrokkeneIdentificatie": check_variable(variables, "betrokkene"),
        }
        rol = zrc_client.create("rol", data,)
        return rol

    def perform(self):
        rol = self.create_rol()
        return {"rolUrl": rol["url"]}
