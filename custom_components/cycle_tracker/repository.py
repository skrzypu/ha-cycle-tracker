"""Local Store-backed adapter for the PeriodRepository port."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .domain.date_serial import serial_to_date
from .domain.models import Period, legacy_period_id
from .domain.ports import PeriodRepository
from .domain.validation import InvalidRowReport, validate_period_rows
from .sheets import SheetsClient

_LOGGER = logging.getLogger(__name__)

REQUIRED_COLUMNS = (
    "period_id",
    "start_date",
    "end_date",
    "flow_intensity",
    "notes",
    "updated_at",
)


def _serialize_period(period: Period) -> dict[str, Any]:
    """Serialize a Period to the persisted row shape.

    An open period is stored with ``end_date == start_date`` so that legacy
    consumers and the calendar adapter keep working.
    """
    row: dict[str, Any] = {
        "period_id": str(period.id),
        "start_date": period.start.isoformat(),
        "end_date": (period.end or period.start).isoformat(),
        "flow_intensity": period.flow,
        "notes": period.notes,
    }
    if period.updated_at is not None:
        row["updated_at"] = period.updated_at.isoformat()
    else:
        row["updated_at"] = None
    return row


def _deserialize_period(row: dict[str, Any]) -> Period | None:
    """Adapt one stored row to a Period, warning instead of raising."""
    raw_start = row.get("start_date")
    if not isinstance(raw_start, str):
        _LOGGER.warning("Ignoring stored period without a start date: %s", row)
        return None
    try:
        start = date.fromisoformat(raw_start)
    except ValueError:
        _LOGGER.warning("Ignoring stored period with an invalid start: %s", row)
        return None

    period_id: UUID
    raw_id = row.get("period_id")
    if isinstance(raw_id, str):
        try:
            period_id = UUID(raw_id)
        except ValueError:
            _LOGGER.warning(
                "Ignoring invalid period_id %r, deriving legacy id for start %s",
                raw_id,
                raw_start,
            )
            period_id = legacy_period_id(start)
    else:
        period_id = legacy_period_id(start)

    raw_end = row.get("end_date")
    end: date | None = None
    if raw_end is not None:
        try:
            end = date.fromisoformat(raw_end)
        except (TypeError, ValueError):
            _LOGGER.warning("Ignoring stored period with an invalid end: %s", row)
            return None
        if end < start:
            _LOGGER.warning("Ignoring stored period ending before its start: %s", row)
            return None
        if end == start:
            # The logging contract stores ``end_date == start_date`` for a
            # period that has not ended yet, so an equal end marks it open.
            end = None

    flow = row.get("flow_intensity")
    notes = row.get("notes")
    updated_at: datetime | None = None
    raw_updated = row.get("updated_at")
    if isinstance(raw_updated, str):
        try:
            updated_at = datetime.fromisoformat(raw_updated)
        except ValueError:
            _LOGGER.warning(
                "Ignoring invalid updated_at %r for period %s", raw_updated, period_id
            )

    return Period(
        id=period_id,
        start=start,
        end=end,
        flow=flow,
        notes=notes,
        updated_at=updated_at,
    )


class SheetSchemaError(Exception):
    """The worksheet header is missing one or more required columns."""

    def __init__(self, missing_columns: list[str]) -> None:
        """Initialize with the column names that were not found."""
        self.missing_columns = missing_columns
        super().__init__(
            f"Missing required sheet columns: {', '.join(missing_columns)}"
        )


def _header_indices(headers: list[str]) -> dict[str, int]:
    """Map required column names to their zero-based positions."""
    indices: dict[str, int] = {}
    missing: list[str] = []
    for name in REQUIRED_COLUMNS:
        try:
            indices[name] = headers.index(name)
        except ValueError:
            missing.append(name)
    if missing:
        raise SheetSchemaError(missing)
    return indices


def _parse_date_value(value: Any) -> date | None:
    """Parse a raw Sheets cell value as a date."""
    if isinstance(value, str):
        if value == "":
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    if isinstance(value, (int, float)):
        try:
            return serial_to_date(value)
        except (ValueError, OverflowError):
            return None
    return None


class SheetsPeriodRepository(PeriodRepository):
    """Persist periods in a Google Sheets worksheet."""

    def __init__(
        self,
        client: SheetsClient,
        spreadsheet_id: str,
        worksheet: str,
    ) -> None:
        """Initialize the repository with a configured Sheets client."""
        self._client = client
        self._spreadsheet_id = spreadsheet_id
        self._worksheet = worksheet
        self._last_invalid_reports: list[InvalidRowReport] = []

    def _map_row_to_period(
        self,
        headers: list[str],
        row: list[Any],
        row_number: int,
    ) -> Period | None:
        """Adapt one raw sheet row to a Period, or None if start is unusable."""
        indices = _header_indices(headers)

        def cell(name: str) -> Any:
            idx = indices[name]
            return row[idx] if idx < len(row) else ""

        raw_id = cell("period_id")
        raw_start = cell("start_date")
        raw_end = cell("end_date")
        raw_flow = cell("flow_intensity")
        raw_notes = cell("notes")
        raw_updated = cell("updated_at")

        start = _parse_date_value(raw_start)
        if start is None:
            return None

        period_id: UUID
        if isinstance(raw_id, str) and raw_id != "":
            try:
                period_id = UUID(raw_id)
            except ValueError:
                period_id = legacy_period_id(start)
        else:
            period_id = legacy_period_id(start)

        end: date | None = None
        if raw_end not in (None, ""):
            end = _parse_date_value(raw_end)
            if end == start:
                end = None

        flow = raw_flow if raw_flow != "" else None
        notes = raw_notes if raw_notes != "" else None

        updated_at: datetime | None = None
        if isinstance(raw_updated, str) and raw_updated != "":
            try:
                updated_at = datetime.fromisoformat(raw_updated)
            except ValueError:
                pass

        return Period(
            id=period_id,
            start=start,
            end=end,
            flow=flow,
            notes=notes,
            updated_at=updated_at,
        )

    def _period_to_row(self, headers: list[str], period: Period) -> list[Any]:
        """Serialize a Period to a sheet row mapped by header name."""
        indices = _header_indices(headers)
        max_index = max(indices.values())
        row: list[Any] = [""] * (max_index + 1)
        row[indices["period_id"]] = str(period.id)
        row[indices["start_date"]] = period.start.isoformat()
        row[indices["end_date"]] = (
            period.end.isoformat() if period.end is not None else ""
        )
        row[indices["flow_intensity"]] = period.flow if period.flow is not None else ""
        row[indices["notes"]] = period.notes if period.notes is not None else ""
        row[indices["updated_at"]] = (
            period.updated_at.isoformat() if period.updated_at is not None else ""
        )
        return row

    @property
    def last_invalid_reports(self) -> list[InvalidRowReport]:
        """Return reports from the most recent ``read_all`` call."""
        return list(self._last_invalid_reports)

    async def sheet_has_data_rows(self) -> bool:
        """Return True when the worksheet contains any rows beyond the header."""
        rows = await self._client.read_rows(self._spreadsheet_id, self._worksheet)
        return len(rows) > 1

    async def read_all(self) -> list[Period]:
        """Load all valid periods from the worksheet, reporting invalid rows."""
        self._last_invalid_reports = []
        rows = await self._client.read_rows(self._spreadsheet_id, self._worksheet)
        if not rows:
            return []

        headers = rows[0]
        _header_indices(headers)  # validate schema eagerly
        candidates: list[tuple[Period | None, int]] = []
        for row_number, row in enumerate(rows[1:], start=2):
            candidates.append(
                (self._map_row_to_period(headers, row, row_number), row_number)
            )

        valid, reports = validate_period_rows(candidates)
        self._log_reports(reports)
        return valid

    def _log_reports(self, reports: list[InvalidRowReport]) -> None:
        """Warn once per invalid row so the user can clean up the sheet."""
        self._last_invalid_reports = list(reports)
        for report in reports:
            _LOGGER.warning(
                "Ignoring invalid sheet row %s: %s",
                report.row_number,
                report.reason,
            )

    async def upsert(self, period: Period) -> None:
        """Update an existing row or append a new one for the period."""
        rows = await self._client.read_rows(self._spreadsheet_id, self._worksheet)
        if not rows:
            raise SheetSchemaError(list(REQUIRED_COLUMNS))

        headers = rows[0]
        indices = _header_indices(headers)
        period_id_str = str(period.id)

        row_index: int | None = None
        for idx, row in enumerate(rows[1:], start=2):
            if (
                indices["period_id"] < len(row)
                and row[indices["period_id"]] == period_id_str
            ):
                row_index = idx
                break

        values = self._period_to_row(headers, period)
        if row_index is not None:
            await self._client.update_row(
                self._spreadsheet_id, self._worksheet, row_index, values
            )
        else:
            await self._client.append_row(self._spreadsheet_id, self._worksheet, values)

    async def delete(self, period_id: UUID) -> None:
        """Clear the first row whose ``period_id`` matches."""
        rows = await self._client.read_rows(self._spreadsheet_id, self._worksheet)
        if not rows:
            return

        headers = rows[0]
        indices = _header_indices(headers)
        period_id_str = str(period_id)
        width = max(len(headers), len(REQUIRED_COLUMNS))

        for idx, row in enumerate(rows[1:], start=2):
            if (
                indices["period_id"] < len(row)
                and row[indices["period_id"]] == period_id_str
            ):
                await self._client.clear_row(
                    self._spreadsheet_id, self._worksheet, idx, width=width
                )
                return


async def import_cached_periods(
    sheet_repo: SheetsPeriodRepository,
    cached_periods: list[Period],
) -> int:
    """Append cached periods to an empty sheet.

    Returns the number of rows written. Raises ``ValueError`` when the sheet
    already contains data rows; in that case the populated sheet wins and no
    rows are written.
    """
    if await sheet_repo.sheet_has_data_rows():
        raise ValueError("Sheet already contains data; import refused")

    for period in cached_periods:
        await sheet_repo.upsert(period)
    return len(cached_periods)


class LocalStoreRepository(PeriodRepository):
    """Persist periods in Home Assistant's local Store."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the repository with a Store bound to the running hass."""
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def read_all(self) -> list[Period]:
        """Load all periods, migrating legacy rows to have a real id."""
        doc = await self._store.async_load()
        if not isinstance(doc, dict):
            if doc is not None:
                _LOGGER.warning("Ignoring malformed stored data: %s", doc)
            return []

        rows = doc.get("periods")
        if not isinstance(rows, list):
            _LOGGER.warning("Ignoring malformed stored periods: %s", rows)
            return []

        result: list[Period] = []
        for row in rows:
            if not isinstance(row, dict):
                _LOGGER.warning("Ignoring non-dict period row: %s", row)
                continue
            period = _deserialize_period(row)
            if period is None:
                continue
            if "period_id" not in row:
                row["period_id"] = str(period.id)
            result.append(period)

        result.sort(key=lambda period: period.start)
        canonical_rows = [_serialize_period(period) for period in result]
        await self._store.async_save({"periods": canonical_rows})

        return result

    async def upsert(self, period: Period) -> None:
        """Insert or replace the row with the same ``period_id``."""
        doc = await self._store.async_load()
        rows: list[dict[str, Any]]
        if isinstance(doc, dict) and isinstance(doc.get("periods"), list):
            rows = doc["periods"]
        else:
            rows = []

        serialized = _serialize_period(period)
        period_id_str = str(period.id)
        replaced = False
        new_rows: list[dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict) and row.get("period_id") == period_id_str:
                new_rows.append(serialized)
                replaced = True
            else:
                new_rows.append(row)
        if not replaced:
            new_rows.append(serialized)

        new_rows.sort(key=lambda row: row["start_date"])
        await self._store.async_save({"periods": new_rows})

    async def delete(self, period_id: UUID) -> None:
        """Remove the row with the matching id, if present."""
        doc = await self._store.async_load()
        if not isinstance(doc, dict):
            return
        rows = doc.get("periods")
        if not isinstance(rows, list):
            return

        period_id_str = str(period_id)
        new_rows = [
            row
            for row in rows
            if not (isinstance(row, dict) and row.get("period_id") == period_id_str)
        ]
        await self._store.async_save({"periods": new_rows})
