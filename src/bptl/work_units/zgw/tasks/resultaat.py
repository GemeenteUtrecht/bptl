from zgw_consumers.constants import APITypes

from bptl.tasks.registry import register

from .base import ZGWWorkUnit


@register
class CreateResultaatTask(ZGWWorkUnit):
    """
    Set the RESULTAAT for the ZAAK in the process.

    A resultaat is required to be able to close a zaak. A zaak can only have one
    resultaat.

    **Required process variables**

    * ``zaak``: full URL of the ZAAK to set the RESULTAAT for
    * ``resultaattype``: full URL of the RESULTAATTYPE to set
    * ``services``: JSON Object of connection details for ZGW services:

        .. code-block:: json

          {
              "<zrc alias>": {"jwt": "Bearer <JWT value>"},
          }

    **Optional process variables**

    * ``toelichting``

    **Optional process variables (Camunda exclusive)**

    * ``callbackUrl``: send an empty POST request to this URL to signal completion

    **Sets the process variables**

    * ``resultaat``: the full URL of the created RESULTAAT
    """

    def create_resultaat(self):
        zrc_client = self.get_client(APITypes.zrc)
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
