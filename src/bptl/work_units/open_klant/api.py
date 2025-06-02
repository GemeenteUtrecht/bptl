from typing import Dict, Optional, Tuple

from zds_client.client import Client as ZDSClient

from bptl.openklant.client import get_openklant_client
from bptl.work_units.zgw.utils import get_paginated_results


def get_klantcontact_for_interne_taak(
    klantcontact_url: str, client: Optional[ZDSClient] = None
) -> Dict:
    if not client:
        client = get_openklant_client()
    klantcontact = client.retrieve("klantcontact", url=klantcontact_url)
    return klantcontact


def get_details_betrokkene(
    betrokkene_url: str, client: Optional[ZDSClient] = None
) -> Tuple[str, str, str]:

    if not client:
        client = get_openklant_client()

    digital_addresses = get_paginated_results(
        client,
        "digitaleadressen",
        query_params={"verstrektDoorBetrokkene__url": betrokkene_url},
    )

    # get telefoonnummer(s) and emailaddress(es)
    telefoonnummers = []
    emails = []
    for da in digital_addresses:
        if (da.get("soortDigitaalAdres", "") == "email") and (
            email := da.get(
                "adres",
            )
        ):
            emails.append(email)
        elif (da.get("soortDigitaalAdres", "") == "telefoonnummer") and (
            telefoonnummer := da.get(
                "adres",
            )
        ):
            telefoonnummers.append(telefoonnummer)
    email = ", ".join(emails) if emails else "N.B."
    telefoonnummer = ", ".join(telefoonnummers) if telefoonnummers else "N.B."

    # Get volledige naam
    betrokkene = client.retrieve("betrokkene", url=betrokkene_url)
    naam = betrokkene.get("volledigeNaam", "N.B.")
    return naam, email, telefoonnummer
