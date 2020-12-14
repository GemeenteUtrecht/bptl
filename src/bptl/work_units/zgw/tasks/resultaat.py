from zgw_consumers.constants import APITypes

from bptl.tasks.base import check_variable
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

    * ``zaakUrl``: full URL of the ZAAK to set the RESULTAAT for
    * ``resultaattype``: full URL of the RESULTAATTYPE to set
    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls.
    * ``services``: DEPRECATED - support will be removed in 1.1

    **Optional process variables**

    * ``toelichting``

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion

    **Sets the process variables**

    * ``resultaatUrl``: the full URL of the created RESULTAAT
    """

    def create_resultaat(self):
        variables = self.task.get_variables()

        zrc_client = self.get_client(APITypes.zrc)

        # recently renamed zaak -> zaakUrl: handle correctly
        zaak = variables.get("zaakUrl", variables.get("zaak"))
        resultaattype = check_variable(variables, "resultaattype")
        toelichting = variables.get("toelichting", "")

        data = {
            "zaak": zaak,
            "resultaattype": resultaattype,
            "toelichting": toelichting,
        }

        resultaat = zrc_client.create("resultaat", data)
        return resultaat

    def perform(self):
        resultaat = self.create_resultaat()
        return {"resultaatUrl": resultaat["url"]}
