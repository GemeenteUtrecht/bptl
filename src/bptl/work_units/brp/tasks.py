from collections import namedtuple
from typing import Iterable, Optional, Tuple

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


Person = namedtuple("Person", ["bsn", "type", "distance"])


class Relations:
    def __init__(self, subject: str):
        self.subject = subject
        self.people = []

    def included(self, bsn: str) -> bool:
        for p in self.people:
            if p.bsn == bsn:
                return True
        return False

    def add_relations(self, ids: Iterable, relation_type: str, distance: int):
        for bsn in ids:
            if not self.included(bsn):
                self.people.append(Person(bsn, relation_type, distance))

    def get_person(self, bsn: str) -> Optional[Person]:
        for p in self.people:
            if p.bsn == bsn:
                return p

        return None

    def kinship(self, relations) -> Optional[int]:
        kinships = []
        for external_person in relations.people:
            if self.included(external_person.bsn):
                person = self.get_person(external_person.bsn)
                # exclude relations based by children (spouses, in-laws)
                if not (person.type == "child" and external_person.type == "child"):
                    kinships.append(external_person.distance + person.distance)

        if kinships:
            return min(kinships)
        return None


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
    def request_relations(client, bsn) -> Tuple[list, list]:
        url = f"ingeschrevenpersonen/{bsn}"
        response = client.get(
            url,
            params={
                "expand": "kinderen.burgerservicenummer,ouders.burgerservicenummer"
            },
        )["_embedded"]
        parents = [rel["burgerservicenummer"] for rel in response.get("ouders", [])]
        children = [rel["burgerservicenummer"] for rel in response.get("kinderen", [])]
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
        parents1, children1 = self.request_relations(client, bsn1)
        rel1 = Relations(bsn1)
        rel1.add_relations(parents1, "parent", 1)
        rel1.add_relations(children1, "child", 1)

        has_degree_kinship_1 = rel1.included(bsn2)
        if kinship == 1:
            return {"hasDegreeOfKinship": has_degree_kinship_1}

        if has_degree_kinship_1:
            return {"hasDegreeOfKinship": False}

        # 2. request 1-level relations of the 2nd person
        parents2, children2 = self.request_relations(client, bsn2)
        rel2 = Relations(bsn1)
        rel2.add_relations(parents2, "parent", 1)
        rel2.add_relations(children2, "child", 1)

        actual_kinship = rel1.kinship(rel2)

        if actual_kinship:
            if kinship == actual_kinship:
                return {"hasDegreeOfKinship": True}
            return {"hasDegreeOfKinship": False}

        # 3. Request 2-level relations of the 1st and 2nd people
        for rel in parents1:
            parents, children = self.request_relations(client, rel)
            rel1.add_relations(parents, "parent", 2)
            rel1.add_relations(children, "child", 2)
        for rel in children1:
            parents, children = self.request_relations(client, rel)
            # don't use parent relations on children
            rel1.add_relations(children, "child", 2)

        for rel in parents2:
            parents, children = self.request_relations(client, rel)
            rel2.add_relations(parents, "parent", 2)
            rel2.add_relations(children, "child", 2)
        for rel in children2:
            parents, children = self.request_relations(client, rel)
            # don't use parent relations on children
            rel2.add_relations(children, "child", 2)

        actual_kinship = rel1.kinship(rel2)
        if kinship == actual_kinship:
            return {"hasDegreeOfKinship": True}
        return {"hasDegreeOfKinship": False}
