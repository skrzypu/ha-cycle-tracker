"""End-to-end persistence: a restart must reproduce the same numbers.

The integration keeps its rows in the Home Assistant ``Store``. These tests
cover the two ways a restart can find them: rows written by the logging
services in this session, and rows already on disk before the first setup. Both
must drive the same three-period prediction, because a restart is exactly where
an adapter that keeps state in memory instead of storage would drift.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import (
    ATTR_AVERAGE_CYCLE_LENGTH,
    ATTR_PREDICTION_CONFIDENCE,
    ATTR_USABLE_CYCLE_COUNT,
    STORAGE_KEY,
    STORAGE_VERSION,
)

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

#: Rows written by the logging services for the shared three-period history.
SERVICE_ROWS = [
    {
        "start_date": "2026-09-16",
        "end_date": "2026-09-20",
        "flow_intensity": "medium",
    },
    {
        "start_date": "2026-10-16",
        "end_date": "2026-10-20",
        "flow_intensity": "medium",
    },
    {
        "start_date": "2026-11-10",
        "end_date": "2026-11-10",  # still open: end equals start
        "flow_intensity": "medium",
    },
]


def _survey(state_of: Callable[[str], Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    """Snapshot every public value the integration exposes as a sensor."""
    return {
        entity_id: (state_of(entity_id).state, dict(state_of(entity_id).attributes))
        for entity_id in SENSORS
    }


async def test_a_restart_reproduces_the_entities_from_storage(
    hass: HomeAssistant,
    started_entry: MockConfigEntry,
    closed_period: Callable[..., Awaitable[None]],
    log_period: Callable[..., Awaitable[None]],
    state_of,
    calendar_events: Callable[[date, date], Awaitable[list[dict[str, object]]]],
) -> None:
    """Log history, restart the entry, and get identical states back.

    The stored payload is asserted first so the restart cannot pass by
    recomputing from data that was never persisted; the second half compares a
    full survey of the seven sensors and the calendar after the entry is set up
    again from the Home Assistant Store.
    """
    await closed_period(date(2026, 9, 16))
    await closed_period(date(2026, 10, 16))
    await log_period(date(2026, 11, 10))

    store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    assert await store.async_load() == {"periods": SERVICE_ROWS}

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


async def test_rows_already_in_storage_drive_the_first_prediction(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    config_entry: MockConfigEntry,
    frozen_today: date,
    state_of,
) -> None:
    """A first setup after a restart reads the rows instead of starting empty.

    The payload is what a previous Home Assistant session wrote, including an
    open period whose end equals its start. Loading it must yield the same
    weighted 27-day prediction as logging the same periods through the
    services.
    """
    hass_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "minor_version": 1,
        "data": {"periods": SERVICE_ROWS},
    }

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
