import io
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pytz
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet
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


def _load_wb(binary: bytes) -> Workbook:
    return load_workbook(io.BytesIO(binary))


def _wb_to_bytes(wb: Workbook) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def _ensure_new_sheet(wb: Workbook, name: str) -> Worksheet:
    # Replace existing sheet of the same name to avoid duplicates
    if name in wb.sheetnames:
        ws = wb[name]
        wb.remove(ws)
    return wb.create_sheet(title=name)


def _daterange(start: datetime, end: datetime) -> Iterable[datetime]:
    """Inclusive date range at day resolution."""
    cur = start
    one_day = timedelta(days=1)
    while cur.date() <= end.date():
        yield cur
        cur = cur + one_day


def add_users_sheet_xlsx(
    report_excel: bytes,
    results_user_logins: List[Dict[str, Any]],
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
    date_format: str = "%Y-%m-%d",
    sheet_name: str = "gebruikers",
) -> bytes:
    """
    Add a 'gebruikers' sheet with columns:
        naam, email, gebruikersnaam, totaal, <each date between start_period and end_period>

    Rows are ordered by 'naam'. If a user's logins_per_day lacks a date, fill 0.

    Arguments:
        report_excel: workbook bytes to augment.
        results_user_logins: list of dicts:
            {
              "naam": str,
              "email": str,
              "gebruikersnaam": str,
              "total_logins": int,
              "logins_per_day": {"YYYY-MM-DD": int, ...}
            }
        start_period/end_period: optional ISO datetime strings. If omitted, range is inferred
            from union of all logins_per_day date keys. When provided, they define the
            complete header date range (inclusive).
        date_format: format used in header cells for dates.
    """
    wb = _load_wb(report_excel)

    # Determine date range
    if start_period and end_period:
        start_dt = datetime.fromisoformat(start_period)
        end_dt = datetime.fromisoformat(end_period)
    else:
        # Infer from data
        min_d: Optional[datetime] = None
        max_d: Optional[datetime] = None
        for u in results_user_logins or []:
            per_day = u.get("logins_per_day", {}) or {}
            for ds in per_day.keys():
                try:
                    d = datetime.fromisoformat(ds)
                except ValueError:
                    # Fallback: accept plain date (YYYY-MM-DD)
                    d = datetime.strptime(ds, "%Y-%m-%d")
                if (min_d is None) or (d < min_d):
                    min_d = d
                if (max_d is None) or (d > max_d):
                    max_d = d
        # If still None (no data), set a single-day range to avoid empty headers
        if min_d is None or max_d is None:
            today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            min_d = max_d = today
        start_dt, end_dt = min_d, max_d

    # Build ordered date headers
    date_headers = [d.strftime(date_format) for d in _daterange(start_dt, end_dt)]

    ws = _ensure_new_sheet(wb, sheet_name)
    headers = ["naam", "email", "gebruikersnaam", "totaal", *date_headers]
    ws.append(headers)

    # Sort rows by 'naam' (fallback to empty string)
    sorted_users = sorted(
        results_user_logins or [], key=lambda u: (u.get("naam") or "").lower()
    )

    for u in sorted_users:
        naam = u.get("naam", "") or ""
        email = u.get("email", "") or ""
        gebruikersnaam = u.get("gebruikersnaam", "") or ""
        totaal = u.get("total_logins", 0) or 0

        per_day: Dict[str, int] = u.get("logins_per_day", {}) or {}
        # Normalize per_day keys to the chosen date_format for robust lookup
        normalized_per_day: Dict[str, int] = {}
        for k, v in per_day.items():
            # Accept both "YYYY-MM-DD" and ISO datetime strings
            try:
                dt = datetime.fromisoformat(k)
            except ValueError:
                dt = datetime.strptime(k, "%Y-%m-%d")
            normalized_per_day[dt.strftime(date_format)] = int(v or 0)

        row = [naam, email, gebruikersnaam, int(totaal)]
        row.extend(normalized_per_day.get(dh, 0) for dh in date_headers)
        ws.append(row)

    return _wb_to_bytes(wb)


def add_informatieobjecten_sheet_xlsx(
    report_excel: bytes,
    results_informatieobjecten: List[Dict[str, Any]],
    sheet_name: str = "informatieobjecten",
    date_out_format: str = "%Y-%m-%d %H:%M:%S",
) -> bytes:
    """
    Add an 'informatieobjecten' sheet with columns:
        auteur, bestandsnaam, informatieobjecttype, creatiedatum, gerelateerde zaken

    Rows are ordered by 'creatiedatum' (None last). The 'gerelateerde zaken' column
    concatenates the list into a comma-separated string.
    """
    wb = _load_wb(report_excel)
    ws = _ensure_new_sheet(wb, sheet_name)

    headers = [
        "auteur",
        "bestandsnaam",
        "informatieobjecttype",
        "creatiedatum",
        "gerelateerde zaken",
    ]
    ws.append(headers)

    # Sort by creatiedatum ascending, None last
    def _key(item: Dict[str, Any]):
        cd = item.get("creatiedatum")
        # Allow str/None/datetime
        if isinstance(cd, str) and cd:
            try:
                cd_dt = datetime.fromisoformat(cd)
            except ValueError:
                # Try common fallback without 'T'
                try:
                    cd_dt = datetime.strptime(cd, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    cd_dt = None
        elif isinstance(cd, datetime):
            cd_dt = cd
        else:
            cd_dt = None
        # Return tuple: (is_none, value) so None sorts last
        return (cd_dt is None, cd_dt or datetime.max)

    sorted_rows = sorted(results_informatieobjecten or [], key=_key)

    for item in sorted_rows:
        auteur = item.get("auteur", "") or ""
        bestandsnaam = item.get("bestandsnaam", "") or ""
        iot = item.get("informatieobjecttype", "") or ""

        cd = item.get("creatiedatum")
        if isinstance(cd, datetime):
            cd_str = cd.strftime(date_out_format)
        elif isinstance(cd, str):
            # Leave as-is if already string
            cd_str = cd
        else:
            cd_str = ""

        # Accept both "gerelateerde zaken" and "gerelateerde_zaken" keys
        gz = item.get("gerelateerde zaken")
        if gz is None:
            gz = item.get("gerelateerde_zaken")
        if isinstance(gz, list):
            gz_str = ", ".join([str(x) for x in gz])
        else:
            gz_str = str(gz or "")

        ws.append([auteur, bestandsnaam, iot, cd_str, gz_str])

    return _wb_to_bytes(wb)
