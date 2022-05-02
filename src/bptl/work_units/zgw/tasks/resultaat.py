from unittest import result

from zgw_consumers.constants import APITypes

from bptl.tasks.base import MissingVariable, check_variable
from bptl.tasks.registry import register

from .base import ZGWWorkUnit, require_zrc


@register
@require_zrc
class CreateResultaatTask(ZGWWorkUnit):
    """
    Set the RESULTAAT for the ZAAK in the process.

    A resultaat is required to be able to close a zaak. A zaak can only have one
    resultaat.

    **Required process variables**

    * ``zaakUrl``: full URL of the ZAAK to set the RESULTAAT for.
    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.
    * ``resultaattype``: full URL of the RESULTAATTYPE to set.

      **OR**

    * ``omschrijving``: description of RESULTAAT.

    **Optional process variables**

    * ``toelichting``

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion.

    **Sets the process variables**

    * ``resultaatUrl``: the full URL of the created RESULTAAT.
    """

    def _get_resultaattype(self, zaak_url: str, variables: dict) -> str:
        try:
            resultaattype = check_variable(variables, "resultaattype")
        except MissingVariable:
            try:
                omschrijving = check_variable(variables, "omschrijving")
            except MissingVariable:
                raise MissingVariable(
                    "Missing both resultaattype and omschrijving. One is required."
                )
            else:
                zrc_client = self.get_client(APITypes.zrc)
                zaak = zrc_client.retrieve("zaak", url=zaak_url)
                ztc_client = self.get_client(APITypes.ztc)
                resultaattypen = ztc_client.list(
                    "resultaattype",
                    request_kwargs={"params": {"zaaktype": zaak["zaaktype"]}},
                )
                if resultaattypen["count"] == 0:
                    raise ValueError(
                        "No resultaattypen were found for zaaktype %s."
                        % zaak["zaaktype"]
                    )
                resultaattype = [
                    rt
                    for rt in resultaattypen["results"]
                    if rt["omschrijving"].lower() == omschrijving.lower()
                ]
                if len(resultaattype) != 1:
                    raise ValueError(
                        "No%s resultaattype was found with zaaktype %s and omschrijving %s."
                        % (
                            "" if len(resultaattype) == 0 else " unique",
                            zaak["zaaktype"],
                            omschrijving,
                        )
                    )
                resultaattype = resultaattype[0]["url"]
        return resultaattype

    def create_resultaat(self):
        variables = self.task.get_variables()

        # recently renamed zaak -> zaakUrl: handle correctly
        zaak_url = variables.get("zaakUrl", variables.get("zaak"))

        resultaattype = self._get_resultaattype(zaak_url, variables)
        toelichting = variables.get("toelichting", "")

        data = {
            "zaak": zaak_url,
            "resultaattype": resultaattype,
            "toelichting": toelichting,
        }
        zrc_client = self.get_client(APITypes.zrc)
        resultaat = zrc_client.create("resultaat", data)
        return resultaat

    def perform(self):
        resultaat = self.create_resultaat()
        return {"resultaatUrl": resultaat["url"]}
