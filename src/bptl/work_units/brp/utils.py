from collections import namedtuple
from typing import Iterable, Optional, Tuple


def request_relations(client, bsn) -> Tuple[list, list]:
    url = f"ingeschrevenpersonen/{bsn}"
    response = client.get(
        url,
        params={"expand": "kinderen.burgerservicenummer,ouders.burgerservicenummer"},
    )["_embedded"]
    parents = [rel["burgerservicenummer"] for rel in response.get("ouders", [])]
    children = [rel["burgerservicenummer"] for rel in response.get("kinderen", [])]
    return parents, children


Person = namedtuple("Person", ["bsn", "type", "distance"])


class Relations:
    """
    class to store parent and child relations of subject node
    It's not a graph since we don't have to know relations between all the nodes.
    For kinship purposes we must know:
    * the distance of the node from the subject (i.e. kinship)
    * the type of last connection: 'child', 'parent' or 'origin', the latter is used only
    for the main subject of relations. We keep the type, since we don't consider relations based on
    mutual children (partners, in-laws)
    Therefore we use Person namedtuples to store all necessary data about each node
    """

    def __init__(self, subject: str):
        self.subject = subject
        self.people = [Person(bsn=subject, type="origin", distance=0)]

    def included(self, bsn: str) -> bool:
        """ check if requested bsn is in the relations set. Return boolean"""
        for p in self.people:
            if p.bsn == bsn:
                return True
        return False

    def add_relations(self, ids: Iterable, relation_type: str, distance: int):
        """ If the requested bsn is not in relations yet, add it to the relations"""
        for bsn in ids:
            if not self.included(bsn):
                self.people.append(Person(bsn, relation_type, distance))

    def get_person(self, bsn: str) -> Optional[Person]:
        """retrieve Person object based on bsn"""
        for p in self.people:
            if p.bsn == bsn:
                return p

        return None

    def kinship(self, relations) -> Optional[int]:
        """
        calculate kinship of subjects of two relations
        """
        if relations.subject == self.subject:
            return None

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

    def expand(self, client, distance: int):
        """
        expands relations with BRP api for specified level (distance)
        For example, calling rel.expand(2) means that relations will be requested
        for all Person objects with distance = 1 and the relations set will be
        increased on these relations.
        All relations are considered but relations based on mutual children (partners, in-laws)
        """
        if not distance:
            return

        if distance == 1:
            parents, children = request_relations(client, self.subject)
            self.add_relations(parents, "parent", distance)
            self.add_relations(children, "child", distance)

        else:
            # requests relations for level-1 nodes
            for person in self.people:
                if person.distance == distance - 1:
                    parents, children = request_relations(client, person.bsn)
                    self.add_relations(children, "child", distance)
                    # exclude parent relations based by children
                    if person.type != "child":
                        self.add_relations(parents, "parent", distance)
