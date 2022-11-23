from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .client import get_client, require_brp_service
from .utils import Relations

__all__ = ["IsAboveAge", "DegreeOfKinship"]


@register
@require_brp_service
class IsAboveAge(WorkUnit):
    """
    Fetches BRP API and returns whether a person is exactly, or older than, a certain age.

    **Required process variables**

    * ``burgerservicenummer`` [str]: BSN of the person.
    * ``age`` [int]: which represents the number of years.

    **Optional process variables**

    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    **The task sets the process variables**

    * ``isAboveAge`` [bool]: indicates if the requested person is equal or above a certain age.
      If the information about person's age is not found, ``isAboveAge`` will be set as ``None``.
    """

    def perform(self) -> dict:
        variables = self.task.get_variables()
        bsn = variables["burgerservicenummer"]
        age = variables["age"]

        url = f"ingeschrevenpersonen/{bsn}"

        with get_client(self.task) as client:
            response = client.get(url, params={"fields": "leeftijd"})

        leeftijd = response.get("leeftijd")
        is_above_age = None if leeftijd is None else leeftijd >= age

        return {"isAboveAge": is_above_age}


@register
@require_brp_service
class DegreeOfKinship(WorkUnit):
    """
    Retrieve the degree of kinship from the BRP API.

    **Required process variables**

    * ``burgerservicenummer1`` [str]: BSN of the first person.
    * ``burgerservicenummer2`` [str]: BSN of the second person.

    **Optional process variables**

    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    **Sets the process variables**

    * ``kinship`` [int]: which represents the degree of kinship (blood relations). Values can be in
      range [1..4] or ``Null`` if the BSNs are identical.
    """

    def perform(self) -> dict:
        variables = self.task.get_variables()
        bsn1 = variables["burgerservicenummer1"]
        bsn2 = variables["burgerservicenummer2"]

        if bsn1 == bsn2:
            return {"kinship": None}

        # set up classes for storing parent and child relations of one node
        rel1 = Relations(bsn1)
        rel2 = Relations(bsn2)

        with get_client(self.task) as client:
            # 1. request 1-level relations (child-parend kinship)
            rel1.expand(client, 1)
            rel2.expand(client, 1)

            # search for intersectipns between two relations sets
            kinship = rel1.kinship(rel2)

            if kinship:
                return {"kinship": kinship}

            # 2. Request 2-level relations (siblings and grandparents-grandchildren kinship)
            rel1.expand(client, 2)
            rel2.expand(client, 2)

        # search for intersectipns between two relations sets
        kinship = rel1.kinship(rel2)
        return {"kinship": kinship}
