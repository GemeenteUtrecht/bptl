import io
from datetime import datetime, timedelta
from typing import Dict, Tuple

import pytz
from openpyxl import Workbook
from zgw_consumers.api_models.constants import RolTypes

from bptl.camunda.constants import AssigneeTypeChoices
from bptl.tasks.models import BaseTask

from .client import get_client


def get_betrokkene_identificatie(rol: Dict, task: BaseTask) -> Dict:
    if not (betrokkene_identificatie := rol.get("betrokkeneIdentificatie")):
        betrokkene_identificatie = {}

    if rol.get(
        "betrokkeneType"
    ) == RolTypes.medewerker and f"{AssigneeTypeChoices.user}:" in betrokkene_identificatie.get(
        "identificatie", ""
    ):
        if (
            betrokkene_identificatie.get("voorletters")
            or betrokkene_identificatie.get("voorvoegsel_achternaam")
            or betrokkene_identificatie.get("achternaam")
        ):
            pass
        else:
            with get_client(task) as client:
                betrokkene_identificatie = client.post(
                    f"api/core/rollen/medewerker/betrokkeneIdentificatie",
                    json={"betrokkeneIdentificatie": betrokkene_identificatie},
                ).get("betrokkeneIdentificatie", {})

    return betrokkene_identificatie


def create_zaken_report_xlsx(results) -> bytes:
    # Create Excel workbook in memory
    wb = Workbook()
    ws = wb.active
    ws.title = "Zaken"

    # Write headers
    if results:
        headers = list(results[0].keys())
        ws.append(headers)
        for row in results:
            ws.append([row.get(h, "") for h in headers])

    # Save to buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    data = buffer.read()
    return data


def get_last_month_period(timezone="Europe/Amsterdam") -> Tuple[str, str]:
    """
    Returns two timezone-aware datetimes:
    1. The first day of the previous month at 00:00:00
    2. The last day of the previous month at 23:59:59
    """
    tz = pytz.timezone(timezone)
    today = datetime.now(tz)
    first_of_this_month = today.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    last_month_end = first_of_this_month - timedelta(seconds=1)
    last_month_start = last_month_end.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    last_month_end = last_month_end.replace(
        hour=23, minute=59, second=59, microsecond=0
    ).isoformat()
    return last_month_start, last_month_end
