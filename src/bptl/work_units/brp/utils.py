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
    def __init__(self, subject: str):
        self.subject = subject
        self.people = [Person(bsn=subject, type="origin", distance=0)]

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
        """expands relations with BRP api"""
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
