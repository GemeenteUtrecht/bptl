from typing import Tuple

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
    Fetches BRP API and returns flag if certain two people have a specified degree of kinship

    Required process variables:

    * ``burgerservicenummer1``: BSN of the first person
    * ``burgerservicenummer2``: BSN of the second person
    * ``kinship``: integer, which represents the degree of kinship (blood relations). Values Can be in range [1..4]

    The task sets the process variables:

    * ``hasDegreeOfKinship``: boolean, which indicate if the requested people have a certain degree of kinship.
      If the information about relations is not found or the `kinship`` value is not in the required range,
      ``hasDegreeOfKinship`` will be set as ``none``
    """

    @staticmethod
    def request_relations(client, bsn) -> Tuple[set, set]:
        url = f"ingeschrevenpersonen/{bsn}"
        response = client.get(
            url,
            params={
                "expand": "kinderen.burgerservicenummer,ouders.burgerservicenummer"
            },
        )["_embedded"]
        parents = {rel["burgerservicenummer"] for rel in response.get("ouders", [])}
        children = {rel["burgerservicenummer"] for rel in response.get("kinderen", [])}
        return parents, children

    def perform(self) -> dict:
        variables = self.task.get_variables()
        bsn1 = variables["burgerservicenummer1"]
        bsn2 = variables["burgerservicenummer2"]
        kinship = variables["kinship"]

        if kinship < 1 or kinship > 4:
            return {"hasDegreeOfKinship": None}

        if bsn1 == bsn2:
            return {"hasDegreeOfKinship": None}

        client = get_client_class()()
        client.task = self.task

        # 1. request 1-level relations of the 1st person
        relations1_parents, relations1_children = self.request_relations(client, bsn1)

        has_degree_kinship_1 = bsn2 in relations1_parents | relations1_children
        if kinship == 1:
            return {"hasDegreeOfKinship": has_degree_kinship_1}

        if has_degree_kinship_1:
            return {"hasDegreeOfKinship": False}

        # 2. request 1-level relations of the 2nd person
        relations2_parents, relations2_children = self.request_relations(client, bsn2)

        # parents are not considered related, so we exclude intersection by children
        siblings = bool(relations1_parents & relations2_parents)
        grandchildren = bool(
            (relations1_parents & relations2_children)
            | (relations2_parents & relations1_children)
        )
        has_degree_kinship_2 = siblings or grandchildren
        if kinship == 2:
            return {"hasDegreeOfKinship": has_degree_kinship_2}

        if has_degree_kinship_2:
            return {"hasDegreeOfKinship": False}

        # 3. Request 2-level relations of the 1st and 2nd people
        relations1_parents_parents = set()
        relations1_parents_children = set()
        relations1_children_children = set()
        for rel in relations1_parents:
            parents, children = self.request_relations(client, rel)
            relations1_parents_parents = relations1_parents_parents | parents
            relations1_parents_children = relations1_parents_children | children
        for rel in relations1_children:
            parents, children = self.request_relations(client, rel)
            relations1_children_children = relations1_children_children | children

        relations2_parents_parents = set()
        relations2_parents_children = set()
        relations2_children_children = set()
        for rel in relations2_parents:
            parents, children = self.request_relations(client, rel)
            relations2_parents_parents = relations2_parents_parents | parents
            relations2_parents_children = relations2_parents_children | children
        for rel in relations2_children:
            parents, children = self.request_relations(client, rel)
            relations2_children_children = relations2_children_children | children

        has_degree_kinship_3 = bool(
            (relations1_parents_parents & relations2_parents)
            | (relations1_parents_parents & relations2_children)
            | (relations1_parents_children & relations2_parents)
            | (relations1_children_children & relations2_parents)
            | (relations2_parents_parents & relations1_parents)
            | (relations2_parents_parents & relations1_children)
            | (relations2_parents_children & relations1_parents)
            | (relations2_children_children & relations1_parents)
        )
        if kinship == 3:
            return {"hasDegreeOfKinship": has_degree_kinship_3}

        if has_degree_kinship_3:
            return {"hasDegreeOfKinship": False}

        has_degree_kinship_4 = bool(
            (relations1_parents_parents & relations2_parents_parents)
            | (relations1_parents_parents & relations2_parents_children)
            | (relations1_parents_parents & relations2_children_children)
            | (relations2_parents_parents & relations1_parents_children)
            | (relations2_parents_parents & relations1_children_children)
        )
        return {"hasDegreeOfKinship": has_degree_kinship_4}
