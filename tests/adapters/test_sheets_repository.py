"""Tests for the Google Sheets-backed period repository."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from custom_components.cycle_tracker.domain.models import Period
from custom_components.cycle_tracker.repository import (
    SheetSchemaError,
    SheetsPeriodRepository,
)
from custom_components.cycle_tracker.sheets import SheetsClient


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


async def test_upsert_appends_new_period(
    client: AsyncMock,
    headers: list[str],
) -> None:
    """A period whose id is not present is appended as a new row."""
    client.read_rows.return_value = [headers]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")
    period = Period(
        id=uuid4(),
        start=date(2026, 1, 1),
        end=date(2026, 1, 5),
        flow="light",
        notes="note",
    )

    await repo.upsert(period)

    client.append_row.assert_awaited_once_with(
        "sheet1",
        "Sheet1",
        [str(period.id), "2026-01-01", "2026-01-05", "light", "note", ""],
    )
    client.update_row.assert_not_awaited()


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

    values: list[Any] = client.append_row.call_args.args[2]
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
