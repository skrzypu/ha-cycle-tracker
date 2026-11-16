"""Fixtures for the Cycle Tracker Home Assistant adapter tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from datetime import date, timedelta

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import (
    CONF_CYCLE_LENGTH,
    CONF_LAST_PERIOD_START,
    CONF_PERIOD_LENGTH,
    CONF_PREDICTION_ALGORITHM,
    DOMAIN,
)
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator

# `pytest_homeassistant_custom_component` is registered through its `pytest11`
# entry point, so the Home Assistant fixtures are already available here; pytest
# rejects a `pytest_plugins` declaration outside the rootdir conftest.

FROZEN_TODAY = date(2026, 11, 13)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Iterator[None]:
    """Let Home Assistant load the custom integration under test."""
    yield


@pytest.fixture
def frozen_today(freezer) -> date:
    """Pin the wall clock so the snapshot reference date is deterministic."""
    freezer.move_to("2026-11-13 12:00:00")
    return FROZEN_TODAY


@pytest.fixture
def config_entry(hass) -> MockConfigEntry:
    """Return a registered config entry with the default settings."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_CYCLE_LENGTH: 28,
            CONF_PERIOD_LENGTH: 5,
            CONF_LAST_PERIOD_START: "2026-01-01",
            CONF_PREDICTION_ALGORITHM: "weighted_moving_average",
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def coordinator(
    hass,
    config_entry: MockConfigEntry,
    frozen_today: date,
) -> AsyncIterator[CycleTrackerCoordinator]:
    """Set up the integration and return its coordinator."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    yield coordinator

    await coordinator.async_shutdown()
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
def period_row() -> Callable[..., dict[str, str]]:
    """Return a helper that builds a legacy stored period row."""

    def _period_row(
        start: date,
        length: int = 5,
        flow: str = "medium",
    ) -> dict[str, str]:
        return {
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=length - 1)).isoformat(),
            "flow_intensity": flow,
        }

    return _period_row
