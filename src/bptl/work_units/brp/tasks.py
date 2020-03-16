from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .client import get_client_class
from .utils import Person, Relations, request_relations

__all__ = ["IsAboveAge", "DegreeOfKinship"]


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
class DegreeOfKinship(WorkUnit):
    """
    Fetches BRP API and returns flag if certain two people have a specified degree of kinship

    Required process variables:

    * ``burgerservicenummer1``: BSN of the first person
    * ``burgerservicenummer2``: BSN of the second person

    The task sets the process variables:

    * ``kinship``: integer, which represents the degree of kinship (blood relations). Values can be in range [1..4]
    """

    def perform(self) -> dict:
        variables = self.task.get_variables()
        bsn1 = variables["burgerservicenummer1"]
        bsn2 = variables["burgerservicenummer2"]

        if bsn1 == bsn2:
            return {"hasDegreeOfKinship": None}

        client = get_client_class()()
        client.task = self.task

        rel1 = Relations(bsn1)
        rel2 = Relations(bsn2)

        # 1. request 1-level relations
        rel1.expand(client, 1)
        rel2.expand(client, 1)

        kinship = rel1.kinship(rel2)

        if kinship:
            return {"kinship": kinship}

        # 2. Request 2-level relations
        rel1.expand(client, 2)
        rel2.expand(client, 2)

        kinship = rel1.kinship(rel2)
        return {"kinship": kinship}
