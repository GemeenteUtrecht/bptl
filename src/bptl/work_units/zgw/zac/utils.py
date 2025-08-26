import io
from datetime import date, datetime, timedelta, timezone
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

# -------------------------
# Shared helpers
# -------------------------


def _parse_dt_any(val: Any) -> Optional[datetime]:
    """Parse a value into datetime if possible; supports date, ISO (incl. 'Z'), and common formats."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day)
    if isinstance(val, str) and val:
        s = val.replace("Z", "+00:00")  # support trailing 'Z' (UTC)
        try:
            return datetime.fromisoformat(s)  # handles offsets and naive ISO
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
    return None


def _to_excel_date(val: Any) -> Optional[date]:
    """
    Parse various date/datetime strings (incl. trailing 'Z' or offsets) and
    return a timezone-naive date object for Excel.
    """
    dt = _parse_dt_any(val)
    if not dt:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.date()


def _load_wb(binary: bytes) -> Workbook:
    return load_workbook(io.BytesIO(binary))


def _wb_to_bytes(wb: Workbook) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def _ensure_new_sheet(wb: Workbook, name: str) -> Worksheet:
    """Create a fresh sheet with given name (remove existing if present)."""
    if name in wb.sheetnames:
        wb.remove(wb[name])
    return wb.create_sheet(title=name)


def _daterange(start: datetime, end: datetime) -> Iterable[datetime]:
    """Inclusive date range at day resolution."""
    cur = start
    one_day = timedelta(days=1)
    while cur.date() <= end.date():
        yield cur
        cur = cur + one_day


def _bold_and_freeze_header(ws: Worksheet) -> None:
    """Bold the first row and freeze panes below it."""
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"


def _apply_autofilter(ws: Worksheet, num_cols: int) -> None:
    """Apply an AutoFilter over A1:<last_col_letter><last_row>."""
    last_row = ws.max_row
    last_col_letter = get_column_letter(num_cols)
    ws.auto_filter.ref = f"A1:{last_col_letter}{last_row}"


def _autosize_columns(ws: Worksheet, num_cols: int, padding: int = 2) -> None:
    """Autosize columns to max content width (including header)."""
    for col_idx in range(1, num_cols + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for cell in ws[col_letter]:
            val = "" if cell.value is None else str(cell.value)
            cell_len = max((len(line) for line in val.splitlines()), default=0)
            if cell_len > max_len:
                max_len = cell_len
        ws.column_dimensions[col_letter].width = max_len + padding


# -------------------------
# Domain helpers
# -------------------------


def get_betrokkene_identificatie(rol: Dict[str, Any], task: BaseTask) -> Dict[str, Any]:
    betrokkene_identificatie: Dict[str, Any] = rol.get("betrokkeneIdentificatie") or {}

    if rol.get(
        "betrokkeneType"
    ) == RolTypes.medewerker and f"{AssigneeTypeChoices.user}:" in betrokkene_identificatie.get(
        "identificatie", ""
    ):
        # Only fetch details if initials/prefix/surname are all missing
        if not (
            betrokkene_identificatie.get("voorletters")
            or betrokkene_identificatie.get("voorvoegsel_achternaam")
            or betrokkene_identificatie.get("achternaam")
        ):
            with get_client(task) as client:
                betrokkene_identificatie = client.post(
                    "api/core/rollen/medewerker/betrokkeneIdentificatie",
                    json={"betrokkeneIdentificatie": betrokkene_identificatie},
                ).get("betrokkeneIdentificatie", {})

    return betrokkene_identificatie


def get_last_month_period(timezone_str: str = "Europe/Amsterdam") -> Tuple[str, str]:
    """
    Returns two timezone-aware ISO datetime strings:
    1) First day of previous month 00:00:00
    2) Last day of previous month 23:59:59
    """
    tz = pytz.timezone(timezone_str)
    today = datetime.now(tz)
    first_of_this_month = today.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    last_month_end = first_of_this_month - timedelta(seconds=1)
    last_month_start_iso = last_month_end.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    last_month_end_iso = last_month_end.replace(
        hour=23, minute=59, second=59, microsecond=0
    ).isoformat()
    return last_month_start_iso, last_month_end_iso


# -------------------------
# Report: Zaken
# -------------------------


def create_zaken_report_xlsx(results: List[Dict[str, Any]]) -> bytes:
    """
    Create an Excel workbook for ZAAK results with:
    - Serializer-defined column order and header titles (underscores → spaces, Title Case)
    - Sorted by registratiedatum (oldest first, blanks last)
    - registratiedatum written as Excel date cells (yyyy-mm-dd)
    - Bold + frozen header row, AutoFilter, auto-sized columns
    """
    field_order: List[str] = [
        "identificatie",
        "omschrijving",
        "zaaktype",
        "registratiedatum",
        "initiator",
        "objecten",
        "aantal_informatieobjecten",
    ]
    headers_display: List[str] = [f.replace("_", " ").title() for f in field_order]

    def _normalize_keys(row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize known camelCase → snake_case keys."""
        if "aantalInformatieobjecten" in row and "aantal_informatieobjecten" not in row:
            row["aantal_informatieobjecten"] = row["aantalInformatieobjecten"]
        return row

    # Normalize + sort (use timezone-naive date for sorting)
    normalized = [_normalize_keys(r.copy()) for r in (results or [])]
    sorted_rows = sorted(
        normalized,
        key=lambda item: (
            (d := _to_excel_date(item.get("registratiedatum"))) is None,
            d or date.max,
        ),
    )

    # Build workbook
    wb: Workbook = Workbook()
    ws: Worksheet = wb.active
    ws.title = "Zaken"
    ws.append(headers_display)
    _bold_and_freeze_header(ws)

    # Rows
    for row in sorted_rows:
        out: List[Any] = [row.get(f, "") for f in field_order]
        ws.append(out)

        # Format registratiedatum cell as *date* (naive) if possible
        excel_date = _to_excel_date(row.get("registratiedatum"))
        if excel_date:
            reg_idx = field_order.index("registratiedatum") + 1
            cell = ws.cell(row=ws.max_row, column=reg_idx)
            cell.value = excel_date
            cell.number_format = "yyyy-mm-dd"

    # Finish
    _apply_autofilter(ws, len(headers_display))
    _autosize_columns(ws, len(headers_display))
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()


# -------------------------
# Report: Users
# -------------------------


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
    wb: Workbook = _load_wb(report_excel)

    # Date range for columns (supports ISO, 'Z', etc.)
    if start_period and end_period:
        start_dt = _parse_dt_any(start_period) or datetime.fromisoformat(start_period)
        end_dt = _parse_dt_any(end_period) or datetime.fromisoformat(end_period)
        if end_dt < start_dt:  # defensive swap
            start_dt, end_dt = end_dt, start_dt
    else:
        min_d: Optional[datetime] = None
        max_d: Optional[datetime] = None
        for u in results_user_logins or []:
            per_day = u.get("logins_per_day", {}) or {}
            for ds in per_day.keys():
                d = _parse_dt_any(ds) or datetime.strptime(str(ds), "%Y-%m-%d")
                if min_d is None or d < min_d:
                    min_d = d
                if max_d is None or d > max_d:
                    max_d = d
        if min_d is None or max_d is None:
            today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            min_d = max_d = today
        start_dt, end_dt = min_d, max_d

    date_headers = [d.strftime(date_format) for d in _daterange(start_dt, end_dt)]

    base_headers = ["naam", "email", "gebruikersnaam", "totaal"]
    formatted_base_headers = [h.replace("_", " ").title() for h in base_headers]
    headers = [*formatted_base_headers, *date_headers]

    ws = _ensure_new_sheet(wb, sheet_name)
    ws.append(headers)
    _bold_and_freeze_header(ws)

    # Sort by name
    sorted_users = sorted(
        results_user_logins or [], key=lambda u: (u.get("naam") or "").lower()
    )

    # Write rows
    for u in sorted_users:
        naam = u.get("naam", "") or ""
        email = u.get("email", "") or ""
        gebruikersnaam = u.get("gebruikersnaam", "") or ""
        totaal = int(u.get("total_logins", 0) or 0)

        per_day: Dict[str, Any] = u.get("logins_per_day", {}) or {}
        normalized_per_day: Dict[str, int] = {}
        for k, v in per_day.items():
            dt = _parse_dt_any(k) or datetime.strptime(str(k), "%Y-%m-%d")
            normalized_per_day[dt.strftime(date_format)] = int(v or 0)

        row = [naam, email, gebruikersnaam, totaal]
        row.extend(normalized_per_day.get(dh, 0) for dh in date_headers)
        ws.append(row)

    _apply_autofilter(ws, len(headers))
    _autosize_columns(ws, len(headers))
    return _wb_to_bytes(wb)


# -------------------------
# Report: Informatieobjecten
# -------------------------


def add_informatieobjecten_sheet_xlsx(
    report_excel: bytes,
    results_informatieobjecten: List[Dict[str, Any]],
    sheet_name: str = "Informatieobjecten",
    date_out_format: str = "%Y-%m-%d %H:%M:%S",  # kept for signature compatibility (not used)
) -> bytes:
    """
    Add an 'Informatieobjecten' sheet with columns:
        Auteur, Bestandsnaam, Informatieobjecttype, Creatiedatum, Gerelateerde Zaken

    Sorted by:
        creatiedatum (asc, None last) → informatieobjecttype → bestandsnaam → auteur

    'creatiedatum' is written as an Excel date (yyyy-mm-dd) when parseable.
    Expects 'gerelateerdeZaken' (list[str]) in each item.
    """
    wb = _load_wb(report_excel)
    ws = _ensure_new_sheet(wb, sheet_name)

    headers = [
        "Auteur",
        "Bestandsnaam",
        "Informatieobjecttype",
        "Creatiedatum",
        "Gerelateerde Zaken",
    ]
    ws.append(headers)
    _bold_and_freeze_header(ws)

    def _sort_key(item: Dict[str, Any]) -> Tuple[bool, date, str, str, str]:
        d = _to_excel_date(item.get("creatiedatum"))
        return (
            d is None,
            d or date.max,
            (item.get("informatieobjecttype") or "").lower(),
            (item.get("bestandsnaam") or "").lower(),
            (item.get("auteur") or "").lower(),
        )

    rows = sorted(results_informatieobjecten or [], key=_sort_key)

    for it in rows:
        auteur = it.get("auteur", "") or ""
        bestandsnaam = it.get("bestandsnaam", "") or ""
        iot = it.get("informatieobjecttype", "") or ""
        excel_date = _to_excel_date(it.get("creatiedatum"))

        # Only use gerelateerdeZaken as requested
        gz_list = it.get("gerelateerdeZaken")
        if isinstance(gz_list, list):
            gz_str = ", ".join(str(x) for x in gz_list)
        else:
            gz_str = str(gz_list or "")

        # Append row with placeholder for date (set below if parseable)
        ws.append([auteur, bestandsnaam, iot, None, gz_str])

        # Write date as real Excel date (naive) if parseable, else as raw string (if provided)
        if excel_date:
            c = ws.cell(row=ws.max_row, column=4)
            c.value = excel_date
            c.number_format = "yyyy-mm-dd"
        else:
            dt_raw = it.get("creatiedatum")
            if isinstance(dt_raw, str):
                ws.cell(row=ws.max_row, column=4).value = dt_raw

    _apply_autofilter(ws, len(headers))
    _autosize_columns(ws, len(headers))
    return _wb_to_bytes(wb)
