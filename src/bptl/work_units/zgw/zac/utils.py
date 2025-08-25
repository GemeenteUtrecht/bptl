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


def get_betrokkene_identificatie(rol: Dict[str, Any], task: BaseTask) -> Dict[str, Any]:
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
                    "api/core/rollen/medewerker/betrokkeneIdentificatie",
                    json={"betrokkeneIdentificatie": betrokkene_identificatie},
                ).get("betrokkeneIdentificatie", {})

    return betrokkene_identificatie


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

    wb: Workbook = Workbook()
    ws: Worksheet = wb.active
    ws.title = "Zaken"

    ws.append(headers_display)

    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"

    def _parse_dt(val: Any) -> Optional[datetime]:
        if isinstance(val, datetime):
            return val
        if isinstance(val, date):
            return datetime(val.year, val.month, val.day)
        if isinstance(val, str) and val:
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    continue
            try:
                return datetime.fromisoformat(val)
            except Exception:
                return None
        return None

    def _sort_key(item: Dict[str, Any]) -> Tuple[bool, datetime]:
        dt = _parse_dt(item.get("registratiedatum"))
        return (dt is None, dt or datetime.max)

    sorted_rows: List[Dict[str, Any]] = sorted(results or [], key=_sort_key)

    for row in sorted_rows:
        out: List[Any] = [row.get(f, "") for f in field_order]
        ws.append(out)

        reg_idx: int = field_order.index("registratiedatum") + 1
        dt = _parse_dt(row.get("registratiedatum"))
        if dt:
            c = ws.cell(row=ws.max_row, column=reg_idx)
            c.value = dt
            c.number_format = "yyyy-mm-dd"

    last_row: int = ws.max_row
    last_col_letter: str = get_column_letter(len(headers_display))
    ws.auto_filter.ref = f"A1:{last_col_letter}{last_row}"

    padding: int = 2
    for col_idx in range(1, len(headers_display) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for cell in ws[col_letter]:
            val = "" if cell.value is None else str(cell.value)
            cell_len = max((len(line) for line in val.splitlines()), default=0)
            if cell_len > max_len:
                max_len = cell_len
        ws.column_dimensions[col_letter].width = max_len + padding

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()


def get_last_month_period(timezone: str = "Europe/Amsterdam") -> Tuple[str, str]:
    """
    Returns two timezone-aware datetimes (ISO strings):
    1. The first day of the previous month at 00:00:00
    2. The last day of the previous month at 23:59:59
    """
    tz = pytz.timezone(timezone)
    today = datetime.now(tz)
    first_of_this_month = today.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    last_month_end = first_of_this_month - timedelta(seconds=1)
    last_month_start_iso: str = last_month_end.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    last_month_end_iso: str = last_month_end.replace(
        hour=23, minute=59, second=59, microsecond=0
    ).isoformat()
    return last_month_start_iso, last_month_end_iso


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
        ws_existing = wb[name]
        wb.remove(ws_existing)
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
    wb: Workbook = _load_wb(report_excel)

    if start_period and end_period:
        start_dt: datetime = datetime.fromisoformat(start_period)
        end_dt: datetime = datetime.fromisoformat(end_period)
    else:
        min_d: Optional[datetime] = None
        max_d: Optional[datetime] = None
        for u in results_user_logins or []:
            per_day: Dict[str, Any] = u.get("logins_per_day", {}) or {}
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

    date_headers: List[str] = [
        d.strftime(date_format) for d in _daterange(start_dt, end_dt)
    ]

    base_headers: List[str] = ["naam", "email", "gebruikersnaam", "totaal"]
    formatted_base_headers: List[str] = [
        h.replace("_", " ").title() for h in base_headers
    ]
    headers: List[str] = [*formatted_base_headers, *date_headers]

    ws: Worksheet = _ensure_new_sheet(wb, sheet_name)
    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"

    sorted_users: List[Dict[str, Any]] = sorted(
        results_user_logins or [], key=lambda u: (u.get("naam") or "").lower()
    )

    for u in sorted_users:
        naam: str = u.get("naam", "") or ""
        email: str = u.get("email", "") or ""
        gebruikersnaam: str = u.get("gebruikersnaam", "") or ""
        totaal: int = int(u.get("total_logins", 0) or 0)

        per_day: Dict[str, Any] = u.get("logins_per_day", {}) or {}
        normalized_per_day: Dict[str, int] = {}
        for k, v in per_day.items():
            try:
                dt = datetime.fromisoformat(k)
            except ValueError:
                dt = datetime.strptime(k, "%Y-%m-%d")
            normalized_per_day[dt.strftime(date_format)] = int(v or 0)

        row: List[Any] = [naam, email, gebruikersnaam, totaal]
        row.extend(normalized_per_day.get(dh, 0) for dh in date_headers)
        ws.append(row)

    last_row: int = ws.max_row
    last_col_letter: str = get_column_letter(len(headers))
    ws.auto_filter.ref = f"A1:{last_col_letter}{last_row}"

    padding: int = 2
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
    sheet_name: str = "informatieobjecten",
    date_out_format: str = "%Y-%m-%d %H:%M:%S",
) -> bytes:
    """
    Add an 'Informatieobjecten' sheet with columns:
        Auteur, Bestandsnaam, Informatieobjecttype, Creatiedatum, Gerelateerde Zaken

    Sorted by:
        creatiedatum (asc, None last) → informatieobjecttype → bestandsnaam → auteur

    creatiedatum is written as an Excel date cell with format yyyy-mm-dd if possible.
    Header is bold/frozen, columns auto-sized, and an AutoFilter is applied.
    """
    wb: Workbook = _load_wb(report_excel)
    ws: Worksheet = _ensure_new_sheet(wb, sheet_name)

    base_headers: List[str] = [
        "auteur",
        "bestandsnaam",
        "informatieobjecttype",
        "creatiedatum",
        "gerelateerde zaken",
    ]
    headers: List[str] = [h.replace("_", " ").title() for h in base_headers]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"

    def _parse_dt(cd: Any) -> Optional[datetime]:
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

    def _key(item: Dict[str, Any]) -> Tuple[bool, datetime, str, str, str]:
        cd_dt = _parse_dt(item.get("creatiedatum"))
        iot = (item.get("informatieobjecttype") or "").lower()
        bestandsnaam = (item.get("bestandsnaam") or "").lower()
        auteur = (item.get("auteur") or "").lower()
        return (
            cd_dt is None,
            cd_dt or datetime.max,
            iot,
            bestandsnaam,
            auteur,
        )

    sorted_rows: List[Dict[str, Any]] = sorted(
        results_informatieobjecten or [], key=_key
    )

    for item in sorted_rows:
        auteur: str = item.get("auteur", "") or ""
        bestandsnaam: str = item.get("bestandsnaam", "") or ""
        iot: str = item.get("informatieobjecttype", "") or ""

        cd_val: Any = item.get("creatiedatum")
        cd_dt: Optional[datetime] = _parse_dt(cd_val)

        gz: Any = item.get("gerelateerde zaken")
        if gz is None:
            gz = item.get("gerelateerde_zaken")
        if isinstance(gz, list):
            gz_str = ", ".join([str(x) for x in gz])
        else:
            gz_str = str(gz or "")

        ws.append([auteur, bestandsnaam, iot, None, gz_str])

        if cd_dt:
            cell = ws.cell(row=ws.max_row, column=4)
            cell.value = cd_dt
            cell.number_format = "yyyy-mm-dd"
        elif isinstance(cd_val, str):
            ws.cell(row=ws.max_row, column=4).value = cd_val

    padding: int = 2
    for col_idx, _ in enumerate(headers, start=1):
        column_letter = get_column_letter(col_idx)
        max_len = 0
        for cell in ws[column_letter]:
            val = "" if cell.value is None else str(cell.value)
            cell_len = max((len(line) for line in val.splitlines()), default=0)
            if cell_len > max_len:
                max_len = cell_len
        ws.column_dimensions[column_letter].width = max_len + padding

    last_row: int = ws.max_row
    last_col_letter: str = get_column_letter(len(headers))
    ws.auto_filter.ref = f"A1:{last_col_letter}{last_row}"

    return _wb_to_bytes(wb)
