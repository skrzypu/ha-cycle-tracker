"""Tests for what the integration releases when a config entry is unloaded."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import (
    CONF_CYCLE_LENGTH,
    CONF_LAST_PERIOD_START,
    CONF_PERIOD_LENGTH,
    CONF_PREDICTION_ALGORITHM,
    DOMAIN,
)
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator


def _entry_data() -> dict[str, Any]:
    """Return setup data for an entry this module owns."""
    return {
        CONF_CYCLE_LENGTH: 28,
        CONF_PERIOD_LENGTH: 5,
        CONF_LAST_PERIOD_START: "2026-01-01",
        CONF_PREDICTION_ALGORITHM: "weighted_moving_average",
    }


async def test_unload_shuts_the_coordinator_down(
    hass: HomeAssistant,
) -> None:
    """Unloading stops the coordinator and clears its runtime data."""
    entry = MockConfigEntry(domain=DOMAIN, data=_entry_data())
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    shutdown = AsyncMock(wraps=coordinator.async_shutdown)
    coordinator.async_shutdown = shutdown  # type: ignore[method-assign]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    shutdown.assert_awaited_once()
    assert coordinator._unsub_refresh is None
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_the_coordinator_polls_the_sheet_every_five_minutes(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    config_entry: MockConfigEntry,
) -> None:
    """The running coordinator re-syncs from the sheet on a five-minute cycle.

    README states the sheet is polled every 5 minutes. The interval is spelled
    out as ``timedelta(minutes=5)`` rather than via
    ``DEFAULT_POLL_INTERVAL_MINUTES`` so a drift between the documented value
    and the scheduler fails here. Date-change rebuilds are separate behaviour,
    covered by ``test_snapshot_rebuilds_when_the_reference_date_changes``.
    """
    assert hass.data[DOMAIN][config_entry.entry_id] is coordinator
    assert coordinator.update_interval == timedelta(minutes=5)
