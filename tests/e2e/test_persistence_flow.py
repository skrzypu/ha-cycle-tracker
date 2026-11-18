"""End-to-end persistence: a restart must reproduce the same numbers.

The integration keeps its rows in the user-owned Google Sheet. These tests
cover the two ways a restart can find them: rows written by the logging
services in this session, and rows already in the sheet before the first setup.
Both must drive the same three-period prediction, because a restart is exactly
where an adapter that keeps state in memory instead of the sheet would drift.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any
from uuid import UUID

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import (
    ATTR_AVERAGE_CYCLE_LENGTH,
    ATTR_PREDICTION_CONFIDENCE,
    ATTR_USABLE_CYCLE_COUNT,
)
from custom_components.cycle_tracker.domain.models import legacy_period_id

CYCLE_DAY = "sensor.cycle_tracker_cycle_day"
CYCLE_PHASE = "sensor.cycle_tracker_cycle_phase"
NEXT_PERIOD = "sensor.cycle_tracker_next_period_date"
NEXT_OVULATION = "sensor.cycle_tracker_next_ovulation_date"
DAYS_UNTIL_PERIOD = "sensor.cycle_tracker_days_until_period"
DAYS_UNTIL_OVULATION = "sensor.cycle_tracker_days_until_ovulation"
STATISTICS = "sensor.cycle_tracker_statistics"

SENSORS = (
    CYCLE_DAY,
    CYCLE_PHASE,
    NEXT_PERIOD,
    NEXT_OVULATION,
    DAYS_UNTIL_PERIOD,
    DAYS_UNTIL_OVULATION,
    STATISTICS,
)

CALENDAR_RANGE = (date(2026, 9, 1), date(2027, 1, 1))

#: Rows the logging services write for the shared three-period history.
SERVICE_ROWS = [
    {
        "period_id": str(legacy_period_id(date(2026, 9, 16))),
        "start_date": "2026-09-16",
        "end_date": "2026-09-20",
        "flow_intensity": "medium",
    },
    {
        "period_id": str(legacy_period_id(date(2026, 10, 16))),
        "start_date": "2026-10-16",
        "end_date": "2026-10-20",
        "flow_intensity": "medium",
    },
    {
        "period_id": str(legacy_period_id(date(2026, 11, 10))),
        "start_date": "2026-11-10",
        "end_date": "",  # still open: the sheet leaves the end blank
        "flow_intensity": "medium",
    },
]


def _sheet_rows() -> list[list[Any]]:
    """Order the service rows as worksheet cells for the emulator's header."""
    return [
        [
            row["period_id"],
            row["start_date"],
            row["end_date"],
            row["flow_intensity"],
            "",  # notes
            "",  # updated_at
        ]
        for row in SERVICE_ROWS
    ]


def _survey(state_of: Callable[[str], Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    """Snapshot every public value the integration exposes as a sensor."""
    return {
        entity_id: (state_of(entity_id).state, dict(state_of(entity_id).attributes))
        for entity_id in SENSORS
    }


async def test_a_restart_reproduces_the_entities_from_the_sheet(
    hass: HomeAssistant,
    started_entry: MockConfigEntry,
    sheet_emulator: Any,
    closed_period: Callable[..., Awaitable[None]],
    log_period: Callable[..., Awaitable[None]],
    state_of,
    calendar_events: Callable[[date, date], Awaitable[list[dict[str, object]]]],
) -> None:
    """Log history, restart the entry, and get identical states back.

    The worksheet rows are asserted first so the restart cannot pass by
    recomputing from data that was never persisted; the second half compares a
    full survey of the seven sensors and the calendar after the entry is set up
    again from the Google Sheet.
    """
    await closed_period(date(2026, 9, 16))
    await closed_period(date(2026, 10, 16))
    await log_period(date(2026, 11, 10))

    rows = sheet_emulator.rows
    assert len(rows) == len(SERVICE_ROWS)
    for row, expected_row in zip(rows, SERVICE_ROWS):
        assert UUID(row[0])  # period_id
        assert row[1] == expected_row["start_date"]
        assert row[3] == expected_row["flow_intensity"]
    # Closed periods keep their end date; the open row has no end at all.
    assert [row[2] for row in rows] == ["2026-09-20", "2026-10-20", ""]

    before = _survey(state_of)
    before_events = await calendar_events(*CALENDAR_RANGE)
    assert before[NEXT_PERIOD][0] == "2026-12-07"

    assert await hass.config_entries.async_unload(started_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(started_entry.entry_id)
    await hass.async_block_till_done()

    after = _survey(state_of)
    assert after == before
    assert await calendar_events(*CALENDAR_RANGE) == before_events

    # Restating the contract values keeps "equal to a wrong first render" from
    # passing: the restart must land on the same hard-coded prediction.
    assert after[NEXT_PERIOD][0] == "2026-12-07"
    assert after[NEXT_PERIOD][1][ATTR_USABLE_CYCLE_COUNT] == 2
    assert after[STATISTICS][1][ATTR_AVERAGE_CYCLE_LENGTH] == 27.5
    assert after[STATISTICS][1][ATTR_PREDICTION_CONFIDENCE] == pytest.approx(
        0.3030303, abs=1e-6
    )


async def test_rows_already_in_the_sheet_drive_the_first_prediction(
    hass: HomeAssistant,
    sheet_emulator: Any,
    config_entry: MockConfigEntry,
    frozen_today: date,
    state_of,
) -> None:
    """A first setup after a restart reads the rows instead of starting empty.

    The seeded cells are what a previous Home Assistant session wrote, with the
    open period adapted by an empty end date. Loading them must yield the same
    weighted 27-day prediction as logging the same periods through the
    services.
    """
    sheet_emulator.seed(_sheet_rows())

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    try:
        assert state_of(NEXT_PERIOD).state == "2026-12-07"
        assert state_of(NEXT_PERIOD).attributes[ATTR_USABLE_CYCLE_COUNT] == 2
        assert state_of(STATISTICS).state == "3"
        assert state_of(STATISTICS).attributes[ATTR_AVERAGE_CYCLE_LENGTH] == 27.5
        assert state_of(STATISTICS).attributes[
            ATTR_PREDICTION_CONFIDENCE
        ] == pytest.approx(0.3030303, abs=1e-6)
    finally:
        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()


async def test_external_sheet_edit_is_picked_up_on_refresh(
    hass: HomeAssistant,
    sheet_emulator: Any,
    config_entry: MockConfigEntry,
    frozen_today: date,
    state_of,
) -> None:
    """A row edited or deleted in the sheet drives the next refresh.

    The sheet is the source of truth: after a manual edit (a row deleted here),
    the next poll must follow the sheet instead of the snapshot taken at setup.
    """
    from custom_components.cycle_tracker.const import DOMAIN

    sheet_emulator.seed(_sheet_rows())

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    try:
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        assert len(coordinator.get_domain_periods()) == 3
        assert state_of(STATISTICS).state == "3"

        # External edit: drop the oldest period row from the sheet.
        sheet_emulator.seed(_sheet_rows()[1:])
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        remaining = coordinator.get_domain_periods()
        assert len(remaining) == 2
        assert {period.start for period in remaining} == {
            date(2026, 10, 16),
            date(2026, 11, 10),
        }
        # The published statistics follow the sheet, not the stale snapshot.
        assert state_of(STATISTICS).state == "2"
    finally:
        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()
