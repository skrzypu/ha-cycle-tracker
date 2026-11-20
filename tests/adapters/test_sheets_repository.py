"""Tests for the Google Sheets-backed period repository."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from custom_components.cycle_tracker.domain.models import Period
from custom_components.cycle_tracker.domain.validation import InvalidRowReport
from custom_components.cycle_tracker.repository import (
    SheetSchemaError,
    SheetsPeriodRepository,
)
from custom_components.cycle_tracker.sheets import SheetsApiError, SheetsClient

BLANK_ROW: list[Any] = ["", "", "", "", "", ""]


@pytest.fixture
def headers() -> list[str]:
    """Return the canonical sheet header row."""
    return [
        "period_id",
        "start_date",
        "end_date",
        "flow_intensity",
        "notes",
        "updated_at",
    ]


@pytest.fixture
def client() -> AsyncMock:
    """Return a mocked SheetsClient."""
    return AsyncMock(spec=SheetsClient)


async def test_read_all_round_trips_six_columns_and_ignores_extras(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """A sheet row maps to a Period preserving all six required columns."""
    period_id = uuid4()
    updated_at = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    client.read_rows.return_value = [
        headers + ["extra"],
        [
            str(period_id),
            "2026-01-01",
            "2026-01-05",
            "heavy",
            "a note",
            updated_at.isoformat(),
            "ignored",
        ],
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    periods = await repo.read_all()

    assert len(periods) == 1
    assert periods[0].id == period_id
    assert periods[0].start == date(2026, 1, 1)
    assert periods[0].end == date(2026, 1, 5)
    assert periods[0].flow == "heavy"
    assert periods[0].notes == "a note"
    assert periods[0].updated_at == updated_at


async def test_read_all_open_period_has_empty_end(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """An empty end_date cell becomes ``end=None`` in the domain model."""
    period_id = uuid4()
    client.read_rows.return_value = [
        headers,
        [str(period_id), "2026-01-01", "", "", "", ""],
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    periods = await repo.read_all()

    assert len(periods) == 1
    assert periods[0].id == period_id
    assert periods[0].end is None


async def test_read_all_converts_date_serials(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """UNFORMATTED_VALUE date serials are converted to Python dates."""
    from custom_components.cycle_tracker.domain.date_serial import SHEETS_EPOCH

    start_serial = (date(2026, 1, 1) - SHEETS_EPOCH).days
    end_serial = (date(2026, 1, 5) - SHEETS_EPOCH).days
    client.read_rows.return_value = [
        headers,
        ["", start_serial, end_serial, "", "", ""],
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    periods = await repo.read_all()

    assert len(periods) == 1
    assert periods[0].start == date(2026, 1, 1)
    assert periods[0].end == date(2026, 1, 5)


async def test_read_all_raises_when_required_column_missing(
    client: AsyncMock,
) -> None:
    """A sheet without all required headers is a schema error."""
    client.read_rows.return_value = [
        ["period_id", "start_date"],
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    with pytest.raises(SheetSchemaError) as exc_info:
        await repo.read_all()

    assert "end_date" in exc_info.value.missing_columns
    assert "flow_intensity" in exc_info.value.missing_columns


async def test_read_all_skips_fully_blank_rows_without_reports(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """Fully blank data rows produce no period and no invalid-row report."""
    period_id = uuid4()
    client.read_rows.return_value = [
        headers,
        list(BLANK_ROW),
        [str(period_id), "2026-01-01", "", "", "", ""],
        list(BLANK_ROW),
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    periods = await repo.read_all()

    assert [period.id for period in periods] == [period_id]
    assert repo.last_invalid_reports == []


async def test_read_all_blank_only_sheet_has_no_periods_or_reports(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """A header plus only blank rows reads as completely empty."""
    client.read_rows.return_value = [headers, list(BLANK_ROW), list(BLANK_ROW)]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    assert await repo.read_all() == []
    assert repo.last_invalid_reports == []


async def test_read_all_still_reports_partly_filled_rows_with_bad_start(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """Rows with content but a missing or unparsable start are still reported."""
    client.read_rows.return_value = [
        headers,
        ["", "", "", "", "note but no start", ""],
        ["some-id", "not-a-date", "", "", "", ""],
        [str(uuid4()), "2026-01-01", "", "", "", ""],
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    periods = await repo.read_all()

    assert len(periods) == 1
    assert repo.last_invalid_reports == [
        InvalidRowReport(2, "missing or unparsable start_date"),
        InvalidRowReport(3, "missing or unparsable start_date"),
    ]


async def test_sheet_has_data_rows_ignores_blank_rows(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """A header with only blank data rows does not count as populated."""
    client.read_rows.return_value = [headers, list(BLANK_ROW), list(BLANK_ROW)]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    assert await repo.sheet_has_data_rows() is False


async def test_sheet_has_data_rows_detects_real_row(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """A non-blank data row still counts as sheet data."""
    client.read_rows.return_value = [
        headers,
        [str(uuid4()), "2026-01-01", "", "", "", ""],
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    assert await repo.sheet_has_data_rows() is True


async def test_upsert_new_period_inserts_row_below_header(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """A new id with an occupied row 2 inserts at index 1 then writes row 2."""
    client.read_rows.return_value = [
        headers,
        [str(uuid4()), "2026-01-01", "", "", "", ""],
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")
    period = Period(
        id=uuid4(),
        start=date(2026, 1, 1),
        end=date(2026, 1, 5),
        flow="light",
        notes="note",
    )

    await repo.upsert(period)

    client.insert_row.assert_awaited_once_with("sheet1", "Sheet1")
    client.update_row.assert_awaited_once()
    _, _, row_index, values = client.update_row.call_args.args
    assert row_index == 2
    assert values == [
        str(period.id),
        "2026-01-01",
        "2026-01-05",
        "light",
        "note",
        "",
    ]
    client.append_row.assert_not_awaited()


async def test_upsert_reuses_blank_row_two(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """A new id with an existing blank row 2 writes there without inserting."""
    client.read_rows.return_value = [headers, list(BLANK_ROW)]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")
    period = Period(id=uuid4(), start=date(2026, 1, 1), end=None, flow="medium")

    await repo.upsert(period)

    client.insert_row.assert_not_awaited()
    client.update_row.assert_awaited_once()
    _, _, row_index, values = client.update_row.call_args.args
    assert row_index == 2
    assert values[headers.index("period_id")] == str(period.id)
    client.append_row.assert_not_awaited()


async def test_upsert_partial_failure_propagates_without_second_insert(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """If the value write fails after inserting, the error surfaces with one insert."""
    client.read_rows.return_value = [
        headers,
        [str(uuid4()), "2026-01-01", "", "", "", ""],
    ]
    failure = SheetsApiError({"error": {"code": 500, "message": "write failed"}})
    client.update_row.side_effect = failure
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")
    period = Period(id=uuid4(), start=date(2026, 1, 1), end=None, flow="medium")

    with pytest.raises(SheetsApiError) as exc_info:
        await repo.upsert(period)

    assert exc_info.value is failure
    client.insert_row.assert_awaited_once()
    client.update_row.assert_awaited_once()
    client.append_row.assert_not_awaited()


async def test_upsert_updates_existing_period_by_id(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """A period whose id already exists updates that row in place."""
    period_id = uuid4()
    client.read_rows.return_value = [
        headers,
        [str(period_id), "2026-01-01", "", "", "", ""],
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")
    period = Period(
        id=period_id,
        start=date(2026, 1, 1),
        end=date(2026, 1, 5),
        flow="heavy",
    )

    await repo.upsert(period)

    client.update_row.assert_awaited_once()
    _, _, row_index, values = client.update_row.call_args.args
    assert row_index == 2
    assert values[headers.index("period_id")] == str(period_id)
    assert values[headers.index("end_date")] == "2026-01-05"
    assert values[headers.index("flow_intensity")] == "heavy"
    client.insert_row.assert_not_awaited()
    client.append_row.assert_not_awaited()


async def test_delete_clears_matching_row(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """Deleting a period clears the first row with a matching id."""
    period_id = uuid4()
    client.read_rows.return_value = [
        headers,
        [str(period_id), "2026-01-01", "", "", "", ""],
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    await repo.delete(period_id)

    client.clear_row.assert_awaited_once_with("sheet1", "Sheet1", 2, width=6)


async def test_delete_is_noop_when_id_not_found(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """Deleting a missing id makes no API calls."""
    client.read_rows.return_value = [
        headers,
        [str(uuid4()), "2026-01-01", "", "", "", ""],
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    await repo.delete(uuid4())

    client.clear_row.assert_not_awaited()


async def test_serialized_row_has_no_source_column(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """The row contract contains the six required columns and no source field."""
    client.read_rows.return_value = [headers]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")
    period = Period(id=uuid4(), start=date(2026, 1, 1), end=None)

    await repo.upsert(period)

    values: list[Any] = client.update_row.call_args.args[3]
    assert len(values) == 6
    assert "source" not in headers
    assert all(
        name in headers
        for name in [
            "period_id",
            "start_date",
            "end_date",
            "flow_intensity",
            "notes",
            "updated_at",
        ]
    )
