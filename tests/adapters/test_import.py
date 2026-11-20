"""Tests for one-time import of cached periods into a Google Sheet."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from custom_components.cycle_tracker.domain.models import Period
from custom_components.cycle_tracker.repository import (
    SheetsPeriodRepository,
    import_cached_periods,
)
from custom_components.cycle_tracker.sheets import SheetsClient

HEADERS = [
    "period_id",
    "start_date",
    "end_date",
    "flow_intensity",
    "notes",
    "updated_at",
]


def _client() -> AsyncMock:
    """Return a mocked SheetsClient."""
    return AsyncMock(spec=SheetsClient)


async def test_import_cached_periods_inserts_each_period_at_top() -> None:
    """The first cached period fills blank row 2; later ones insert above it."""
    client = _client()
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    periods = [
        Period(id=uuid4(), start=date(2026, 1, 1), end=date(2026, 1, 5), flow="medium"),
        Period(id=uuid4(), start=date(2026, 2, 1), end=None, flow="light"),
    ]
    empty = [HEADERS]
    with_first = [
        HEADERS,
        [str(periods[0].id), "2026-01-01", "2026-01-05", "medium", "", ""],
    ]
    # sheet_has_data_rows, upsert(first), upsert(second)
    client.read_rows.side_effect = [empty, empty, with_first]

    written = await import_cached_periods(repo, periods)

    assert written == 2
    assert client.update_row.await_count == 2
    assert client.insert_row.await_count == 1
    client.append_row.assert_not_awaited()


async def test_import_cached_periods_fills_header_and_blank_only_sheet() -> None:
    """A sheet holding only blank rows is eligible and its row 2 is filled."""
    client = _client()
    client.read_rows.return_value = [HEADERS, ["", "", "", "", "", ""]]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")
    period = Period(id=uuid4(), start=date(2026, 3, 1), end=None, flow="heavy")

    written = await import_cached_periods(repo, [period])

    assert written == 1
    client.insert_row.assert_not_awaited()
    client.update_row.assert_awaited_once()
    assert client.update_row.call_args.args[2] == 2
    client.append_row.assert_not_awaited()


async def test_import_refuses_when_sheet_already_has_data() -> None:
    """A populated sheet wins and no rows are written."""
    client = _client()
    client.read_rows.return_value = [
        HEADERS,
        [str(uuid4()), "2026-01-01", "2026-01-05", "medium", "", ""],
    ]
    repo = SheetsPeriodRepository(client, "sheet1", "Sheet1")

    periods = [Period(id=uuid4(), start=date(2026, 3, 1), end=None, flow="heavy")]

    with pytest.raises(ValueError, match="Sheet already contains data"):
        await import_cached_periods(repo, periods)

    client.insert_row.assert_not_awaited()
    client.append_row.assert_not_awaited()
    client.update_row.assert_not_awaited()
