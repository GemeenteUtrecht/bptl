import io
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pytz
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
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
    """
    Create an Excel workbook for ZAAK results with:
    - Serializer-defined column order and header titles (underscores → spaces, Title Case)
    - Sorted by registratiedatum (oldest first, blanks last)
    - registratiedatum written as Excel date cells (yyyy-mm-dd)
    - Bold + frozen header row, AutoFilter, auto-sized columns
    """
    # Serializer field order (as specified)
    field_order = [
        "identificatie",
        "omschrijving",
        "zaaktype",
        "registratiedatum",
        "initiator",
        "objecten",
        "aantal_informatieobjecten",
    ]

    # Header display names: "aantal_informatieobjecten" -> "Aantal Informatieobjecten"
    headers_display = [f.replace("_", " ").title() for f in field_order]

    wb = Workbook()
    ws = wb.active
    ws.title = "Zaken"

    # Write headers
    ws.append(headers_display)

    # Style header
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"

    # --- helpers ---
    def _parse_dt(val):
        """Return a datetime for sorting/writing, or None if not parseable."""
        if isinstance(val, datetime):
            return val
        if isinstance(val, date):
            # Convert date -> datetime for consistency
            return datetime(val.year, val.month, val.day)
        if isinstance(val, str) and val:
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    continue
            # Try fromisoformat last (handles offset-naive ISO variants)
            try:
                return datetime.fromisoformat(val)
            except Exception:
                return None
        return None

    def _sort_key(item: dict):
        dt = _parse_dt(item.get("registratiedatum"))
        return (dt is None, dt or datetime.max)

    # Sort oldest -> newest, None last
    sorted_rows = sorted(results or [], key=_sort_key)

    # Write rows (follow field_order)
    for row in sorted_rows:
        out = []
        for f in field_order:
            out.append(row.get(f, ""))
        ws.append(out)

        # Format registratiedatum cell as an Excel date if possible
        reg_idx = field_order.index("registratiedatum") + 1  # 1-based
        dt = _parse_dt(row.get("registratiedatum"))
        if dt:
            c = ws.cell(row=ws.max_row, column=reg_idx)
            c.value = dt
            c.number_format = "yyyy-mm-dd"

    # AutoFilter over all data
    last_row = ws.max_row
    last_col_letter = get_column_letter(len(headers_display))
    ws.auto_filter.ref = f"A1:{last_col_letter}{last_row}"

    # Auto-size columns to max content width (incl. header)
    padding = 2
    for col_idx in range(1, len(headers_display) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for cell in ws[col_letter]:
            val = "" if cell.value is None else str(cell.value)
            cell_len = max((len(line) for line in val.splitlines()), default=0)
            if cell_len > max_len:
                max_len = cell_len
        ws.column_dimensions[col_letter].width = max_len + padding

    # Save
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()


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
    sheet_name: str = "Gebruikers",
) -> bytes:
    """
    Add a 'Gebruikers' sheet with columns:
        Naam, Email, Gebruikersnaam, Totaal, <each date between start_period and end_period>

    Rows are ordered by 'Naam'. If a user's logins_per_day lacks a date, fill 0.
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
                    d = datetime.strptime(ds, "%Y-%m-%d")
                if (min_d is None) or (d < min_d):
                    min_d = d
                if (max_d is None) or (d > max_d):
                    max_d = d
        if min_d is None or max_d is None:
            today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            min_d = max_d = today
        start_dt, end_dt = min_d, max_d

    # Build ordered date headers
    date_headers = [d.strftime(date_format) for d in _daterange(start_dt, end_dt)]

    # Capitalize non-date headers
    base_headers = ["naam", "email", "gebruikersnaam", "totaal"]
    formatted_base_headers = [h.replace("_", " ").title() for h in base_headers]

    headers = [*formatted_base_headers, *date_headers]

    ws = _ensure_new_sheet(wb, sheet_name)
    ws.append(headers)

    # --- style header: bold + freeze top row ---
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"

    # Sort rows by 'naam' (fallback to empty string)
    sorted_users = sorted(
        results_user_logins or [], key=lambda u: (u.get("naam") or "").lower()
    )

    for u in sorted_users:
        naam = u.get("naam", "") or ""
        email = u.get("email", "") or ""
        gebruikersnaam = u.get("gebruikersnaam", "") or ""
        totaal = int(u.get("total_logins", 0) or 0)

        per_day: Dict[str, int] = u.get("logins_per_day", {}) or {}
        # Normalize per_day keys to the chosen date_format for robust lookup
        normalized_per_day: Dict[str, int] = {}
        for k, v in per_day.items():
            try:
                dt = datetime.fromisoformat(k)
            except ValueError:
                dt = datetime.strptime(k, "%Y-%m-%d")
            normalized_per_day[dt.strftime(date_format)] = int(v or 0)

        row = [naam, email, gebruikersnaam, totaal]
        row.extend(normalized_per_day.get(dh, 0) for dh in date_headers)
        ws.append(row)

    # --- apply AutoFilter over the whole data range ---
    last_row = ws.max_row
    last_col_letter = get_column_letter(len(headers))
    ws.auto_filter.ref = f"A1:{last_col_letter}{last_row}"

    # --- auto-size columns to max content width (including header) ---
    padding = 2
    for col_idx in range(1, len(headers) + 1):
        column_letter = get_column_letter(col_idx)
        max_len = 0
        for cell in ws[column_letter]:
            val = "" if cell.value is None else str(cell.value)
            cell_len = max((len(line) for line in val.splitlines()), default=0)
            if cell_len > max_len:
                max_len = cell_len
        ws.column_dimensions[column_letter].width = max_len + padding

    return _wb_to_bytes(wb)


def add_informatieobjecten_sheet_xlsx(
    report_excel: bytes,
    results_informatieobjecten: List[Dict[str, Any]],
    sheet_name: str = "Informatieobjecten",
    date_out_format: str = "%Y-%m-%d %H:%M:%S",  # still used for string fallback
) -> bytes:
    """
    Add an 'Informatieobjecten' sheet with columns:
        Auteur, Bestandsnaam, Informatieobjecttype, Creatiedatum, Gerelateerde Zaken

    Rows are ordered by:
        1. creatiedatum (ascending, None last)
        2. informatieobjecttype
        3. bestandsnaam
        4. auteur

    creatiedatum is written as an Excel date cell with format yyyy-mm-dd if possible.
    Header is bold/frozen, columns auto-sized, and an AutoFilter is applied.
    """
    wb = _load_wb(report_excel)
    ws = _ensure_new_sheet(wb, sheet_name)

    base_headers = [
        "auteur",
        "bestandsnaam",
        "informatieobjecttype",
        "creatiedatum",
        "gerelateerde zaken",
    ]
    headers = [h.replace("_", " ").title() for h in base_headers]
    ws.append(headers)

    # --- make headers bold ---
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # --- freeze top row ---
    ws.freeze_panes = "A2"

    def _parse_dt(cd):
        if isinstance(cd, str) and cd:
            try:
                return datetime.fromisoformat(cd)
            except ValueError:
                try:
                    return datetime.strptime(cd, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return None
        elif isinstance(cd, datetime):
            return cd
        return None

    def _key(item: Dict[str, Any]):
        cd_dt = _parse_dt(item.get("creatiedatum"))
        iot = item.get("informatieobjecttype") or ""
        bestandsnaam = item.get("bestandsnaam") or ""
        auteur = item.get("auteur") or ""
        return (
            cd_dt is None,  # None last
            cd_dt or datetime.max,  # oldest first
            iot.lower(),
            bestandsnaam.lower(),
            auteur.lower(),
        )

    sorted_rows = sorted(results_informatieobjecten or [], key=_key)

    for item in sorted_rows:
        auteur = item.get("auteur", "") or ""
        bestandsnaam = item.get("bestandsnaam", "") or ""
        iot = item.get("informatieobjecttype", "") or ""

        cd_val = item.get("creatiedatum")
        cd_dt = _parse_dt(cd_val)

        gz = item.get("gerelateerde zaken")
        if gz is None:
            gz = item.get("gerelateerde_zaken")
        if isinstance(gz, list):
            gz_str = ", ".join([str(x) for x in gz])
        else:
            gz_str = str(gz or "")

        ws.append([auteur, bestandsnaam, iot, None, gz_str])

        # Excel date cell with yyyy-mm-dd when possible
        if cd_dt:
            cell = ws.cell(row=ws.max_row, column=4)
            cell.value = cd_dt
            cell.number_format = "yyyy-mm-dd"
        elif isinstance(cd_val, str):  # fallback to raw string
            ws.cell(row=ws.max_row, column=4).value = cd_val

    # --- autosize columns ---
    padding = 2
    for col_idx, _ in enumerate(headers, start=1):
        column_letter = get_column_letter(col_idx)
        max_len = 0
        for cell in ws[column_letter]:
            val = "" if cell.value is None else str(cell.value)
            cell_len = max((len(line) for line in val.splitlines()), default=0)
            if cell_len > max_len:
                max_len = cell_len
        ws.column_dimensions[column_letter].width = max_len + padding

    # --- apply AutoFilter over the whole data range ---
    last_row = ws.max_row
    last_col_letter = get_column_letter(len(headers))
    ws.auto_filter.ref = f"A1:{last_col_letter}{last_row}"

    return _wb_to_bytes(wb)
