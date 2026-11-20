"""Tests for daily coordinator scheduling and what unload releases."""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
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


def _sheet_read_count(aioclient_mock: Any) -> int:
    """Count remote sheet reads recorded by the aiohttp test double."""
    return sum(
        1
        for call in aioclient_mock.mock_calls
        if str(call[0]).upper() == "GET" and "sheets.googleapis.com" in str(call[1])
    )


@pytest.fixture
def midnight_timer(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Capture the midnight listener registration instead of scheduling it."""
    captured: dict[str, Any] = {}

    def _fake_track(hass: HomeAssistant, action: Any, **kwargs: Any) -> Any:
        captured["hass"] = hass
        captured["callback"] = action
        captured["kwargs"] = kwargs
        captured["unsub"] = Mock(name="midnight_unsub")
        return captured["unsub"]

    # Patch both plausible import sites so the test does not depend on where
    # the coordinator module happened to bind the helper.
    for module in (
        "custom_components.cycle_tracker.coordinator",
        "custom_components.cycle_tracker",
    ):
        monkeypatch.setattr(
            f"{module}.async_track_time_change", _fake_track, raising=False
        )
    return captured


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

    shutdown.assert_called_once()
    assert coordinator._unsub_refresh is None
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_coordinator_has_no_periodic_update_interval(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    config_entry: MockConfigEntry,
) -> None:
    """The base coordinator is built without a rolling update interval.

    Freshness comes from the local-midnight listener and on-demand refreshes,
    not from a five-minute (or any other) periodic poll.
    """
    assert hass.data[DOMAIN][config_entry.entry_id] is coordinator
    assert coordinator.update_interval is None


async def test_stale_poll_interval_option_does_not_change_scheduling(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    config_entry_data: dict[str, Any],
) -> None:
    """An entry that still carries poll_interval loads with no polling."""
    hass.config_entries.async_update_entry(
        config_entry,
        data={**config_entry_data, "poll_interval": 5},
        options={"poll_interval": 5},
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator.update_interval is None

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_midnight_callback_reads_once_and_republishes(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: Any,
    midnight_timer: dict[str, Any],
) -> None:
    """The registered midnight callback performs one read and one publish."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    assert midnight_timer["hass"] is hass
    assert midnight_timer["kwargs"] == {"hour": 0, "minute": 0}
    assert getattr(midnight_timer["callback"], "__self__", None) is coordinator

    listener = Mock()
    unsub_listener = coordinator.async_add_listener(listener)
    before = _sheet_read_count(aioclient_mock)

    result = midnight_timer["callback"](dt_util.utcnow())
    if inspect.isawaitable(result):
        await result
    await hass.async_block_till_done()

    assert _sheet_read_count(aioclient_mock) == before + 1
    listener.assert_called_once()
    unsub_listener()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_unload_releases_the_midnight_timer(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    midnight_timer: dict[str, Any],
) -> None:
    """Unloading runs the unsub that the coordinator registered on the entry."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    midnight_timer["unsub"].assert_not_called()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    midnight_timer["unsub"].assert_called_once()
