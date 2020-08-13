import logging

from django.utils import timezone

from zgw_consumers.constants import APITypes

from bptl.tasks.base import check_variable
from bptl.tasks.registry import register

from .base import ZGWWorkUnit

logger = logging.getLogger(__name__)


@register
class CreateStatusTask(ZGWWorkUnit):
    """
    Create a new STATUS for the ZAAK in the process.

    **Required process variables**

    * ``zaakUrl``: full URL of the ZAAK to create a new status for
    * ``statusVolgnummer``: volgnummer of the status type as it occurs in the catalogus OR
    * ``statustype``: full URL of the STATUSTYPE to set
    * ``services``: JSON Object of connection details for ZGW services:

        .. code-block:: json

          {
              "<zrc alias>": {"jwt": "Bearer <JWT value>"},
              "<ztc alias>": {"jwt": "Bearer <JWT value>"}
          }

    Note that either ``statusVolgnummer`` or ``statustype`` are sufficient.

    **Optional process variables**

    * ``toelichting``: description of the STATUS

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion

    **Sets the process variables**

    * ``statusUrl``: the full URL of the created STATUS
    """

    def create_status(self) -> dict:
        variables = self.task.get_variables()

        zrc_client = self.get_client(APITypes.zrc)
        zaak_url = check_variable(variables, "zaakUrl")

        if "statusVolgnummer" in variables:
            volgnummer = int(variables["statusVolgnummer"])
            ztc_client = self.get_client(APITypes.ztc)

            logger.info("Deriving statustype URL from Catalogi API")
            zaak = zrc_client.retrieve("zaak", url=zaak_url)

            statustypen = ztc_client.list(
                "statustype", query_params={"zaaktype": zaak["zaaktype"]}
            )

            if statustypen["next"]:
                raise NotImplementedError("Pagination not implemented yet")

            try:
                statustype = next(
                    st["url"]
                    for st in statustypen["results"]
                    if st["volgnummer"] == volgnummer
                )
            except StopIteration:
                raise ValueError(
                    f"Statustype met volgnummer '{variables['statusVolgnummer']}' niet gevonden."
                )
        else:
            statustype = check_variable(variables, "statustype")

        toelichting = variables.get("toelichting", "")
        data = {
            "zaak": zaak_url,
            "statustype": statustype,
            "datumStatusGezet": timezone.now().isoformat(),
            "statustoelichting": toelichting,
        }
        status = zrc_client.create("status", data)
        return status

    def perform(self):
        status = self.create_status()
        return {"statusUrl": status["url"]}
