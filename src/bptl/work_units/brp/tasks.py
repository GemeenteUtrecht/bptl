from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .client import get_client_class

__all__ = ["IsAboveAge", "HasDegreeOfKinship"]


@register
class IsAboveAge(WorkUnit):
    """
    Fetches BRP API and return flag if a certain person is older above a certain age

    Required process variables:

    * ``burgerservicenummer``: BSN of the person
    * ``age``: integer, which represents the number of years

    The task sets the process variables:

    * ``isAboveAge``: boolean, which indicate if the requested person is equal or above a certain age.
      If the information about person's age is not found, ``isAboveAge`` will be set as ``none``
    """

    def perform(self) -> dict:
        variables = self.task.get_variables()
        bsn = variables["burgerservicenummer"]
        age = variables["age"]

        client = get_client_class()()
        client.task = self.task
        url = f"ingeschrevenpersonen/{bsn}"

        response = client.get(url, params={"fields": "leeftijd"})

        leeftijd = response.get("leeftijd")
        is_above_age = None if leeftijd is None else leeftijd >= age

        return {"isAboveAge": is_above_age}


@register
class HasDegreeOfKinship(WorkUnit):
    """
    Fetches BRP API and return flag if a certain two people have a specified degree of kinship

    Required process variables:

    * ``burgerservicenummer1``: BSN of the first person
    * ``burgerservicenummer2``: BSN of the second person
    * ``kinship``: integer, which represents the degree of kinship (blood relations). Values Can be [1..4]

    The task sets the process variables:

    * ``hasDegreeOfKinship``: boolean, which indicate if the requested people have a certain degree of kinship.
      If the information about relations is not found or if `kinship`` value is not in the required range,
      ``hasDegreeOfKinship`` will be set as ``none``
    """

    def perform(self) -> dict:
        variables = self.task.get_variables()
        bsn1 = variables["burgerservicenummer1"]
        bsn2 = variables["burgerservicenummer2"]
        kinship = variables["kinship"]

        if kinship < 1 or kinship > 4:
            return {"hasDegreeOfKinship": None}

        client = get_client_class()()
        client.task = self.task
        url = f"ingeschrevenpersonen/{bsn1}"

        response = client.get(url)
        relations = response["_embedded"]
        parents = relations["ouders"]
        children = relations["kinderen"]

        if kinship == 1:
            for rel in parents + children:
                if rel["burgerservicenummer"] == bsn2:
                    return {"hasDegreeOfKinship": True}

            return {"hasDegreeOfKinship": False}
