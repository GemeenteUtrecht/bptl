import requests

from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .models import BRPConfig

__all__ = ["IsAboveAge"]


@register
class IsAboveAge(WorkUnit):
    """
    Fetches BRP API and return flag if a certain person is older above a certain age

    Required process variables:

    * **burgerservicenummer**: BSN of the person
    * **age**: integer, which represents the number of years

    The task sets the process variables:

    * **isAboveAge**: boolean, which indicate if the requested person is equal or above a certain age.
      If the information about person's age is not found, isAboveAge will be set as ``none``
    """

    def perform(self) -> dict:
        variables = self.task.get_variables()

        bsn = variables["burgerservicenummer"]
        age = variables["age"]

        config = BRPConfig.get_solo()
        headers = config.auth_header
        url = f"{config.api_root}ingeschrevenpersonen/{bsn}"

        response = requests.get(url, {"fields": "leeftijd"}, headers=headers)

        leeftijd = response.json().get("leeftijd")

        is_above_age = None if leeftijd is None else leeftijd >= age

        return {"isAboveAge": is_above_age}
