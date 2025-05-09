import logging
from typing import Dict, List, Optional

from zds_client.client import Client as ZDSClient
from zgw_consumers.concurrent import parallel

from bptl.openklant.client import get_openklant_client
from bptl.openklant.models import OpenKlantConfig
from bptl.work_units.zgw.utils import get_paginated_results

logger = logging.getLogger(__name__)


def get_organisatie_eenheid_email(
    actor_object_id: str, obj_client: Optional[ZDSClient] = None
) -> str:
    if not obj_client:
        config = OpenKlantConfig.get_solo()
        obj_client = config.objects_service.build_client()

    results = get_paginated_results(
        obj_client,
        "object",
        query_params={"data_attr": f"identificatie__exact__{actor_object_id}"},
    )
    if not results:
        logger.warning(
            "Could not find an object at objects-pdf with query parameter data_attr=identificatie__exact__%s."
            % actor_object_id
        )
        return ""
    emails = [
        r["record"]["data"]["email"]
        for r in results
        if r.get("record", {}).get("data", {}).get("email", "")
    ]
    if len(emails) > 1:
        logger.warning(
            "Found more than 1 result with an email address in objects-pdv for identificatie__exact__%s - using default email address."
            % actor_object_id
        )
        return ""
    return emails[0]


def get_actor_email_from_interne_taak(
    interne_taak: Dict, client: Optional[ZDSClient] = None
) -> str:
    actor_urls = [
        actor["url"] for actor in interne_taak.get("toegewezenAanActoren", [])
    ]
    if not actor_urls:
        return ""

    client = get_openklant_client() if not client else client

    def _get_actor_from_url(actor_url: str) -> Dict:
        nonlocal client
        return client.retrieve("actor", url=actor_url)

    with parallel() as executor:
        actoren = list(executor.map(_get_actor_from_url, actor_urls))

    actor_is_medewerker = False
    found_actor = None
    actieve_actoren = [
        actor for actor in actoren if actor.get("indicatieActief", False)
    ]
    if not actieve_actoren:
        return ""

    # Check for medewerkers
    medewerker = [
        actor
        for actor in actieve_actoren
        if actor.get("soortActor", "") == "medewerker"
    ]
    if medewerker:
        emailaddress = [
            mw["actoridentificator"].get("objectId", "")
            for mw in medewerker
            if mw.get("actoridentificator", {}).get("codeSoortObjectId", "") == "email"
        ]
        if len(emailaddress) > 1:
            logger.warning(
                "Found more than 1 active medewerker with an email for OpenKlant interne taak with uuid: %s. Sending to default email address."
                % interne_taak["uuid"]
            )
            return ""
        if not emailaddress:
            logger.warning(
                "Did not find an active medewerker with an email for OpenKlant interne taak with uuid: %s. Sending to default email address."
                % interne_taak["uuid"]
            )
            return ""
        return emailaddress[0]

    # Get organisatie-eenheid emailaddress from objects API
    actoren = [
        actor
        for actor in actieve_actoren
        if actor.get("soortActor", "") == "organisatorische_eenheid"
    ]
    if not actoren:
        logger.warning(
            "Could not find an email address for any of the active actoren for OpenKlant interne taak with uuid: %s. Sending to default email address."
            % interne_taak["uuid"]
        )
        return ""

    # Otherwise try to find email address in objects
    config = OpenKlantConfig.get_solo()
    obj_client = config.objects_service.build_client()
    emailaddress = []
    for actor in actieve_actoren:
        actor_object_id = actor.get("actoridentificator", {}).get("objectId", "")
        if not actor_object_id:
            continue
        else:
            email = get_organisatie_eenheid_email(
                actor_object_id, obj_client=obj_client
            )
            if not email:
                continue
            else:
                emailaddress.append(email)

    if len(emailaddress) > 1:
        logger.warning(
            "Found more than 1 active organisatie eenheid with an email address for OpenKlant interne taak with uuid: %s. Sending to default email address."
        )
        return ""

    if not emailaddress:
        logger.warning(
            "Did not find an active organisatie eenheid with an email for OpenKlant interne taak with uuid: %s. Sending to default email address."
            % interne_taak["uuid"]
        )
        return ""

    return emailaddress[0]
