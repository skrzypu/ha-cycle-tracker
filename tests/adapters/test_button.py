"""Tests for the refresh button platform."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator

REFRESH_BUTTON = "button.cycle_tracker_refresh"


async def test_refresh_button_is_created_enabled_by_default(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    config_entry: MockConfigEntry,
) -> None:
    """The button exists and is not disabled in the entity registry."""
    state = hass.states.get(REFRESH_BUTTON)
    assert state is not None

    registry = er.async_get(hass)
    entry = registry.async_get(REFRESH_BUTTON)
    assert entry is not None
    assert entry.config_entry_id == config_entry.entry_id
    assert entry.disabled_by is None


async def test_pressing_the_button_rereads_the_sheet_once(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    sheet_reads: Callable[[CycleTrackerCoordinator], dict[str, int]],
) -> None:
    """Pressing the button routes through the refresh service."""
    reads = sheet_reads(coordinator)

    await hass.services.async_call(
        "button", "press", {"entity_id": REFRESH_BUTTON}, blocking=True
    )
    await hass.async_block_till_done()

    assert reads["reads"] == 1


async def test_unload_removes_the_button_platform(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Unloading the entry removes the button entity."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(REFRESH_BUTTON) is not None

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    # HA leaves a restored placeholder state; the entity is no longer controlled.
    state = hass.states.get(REFRESH_BUTTON)
    assert state is not None
    assert state.state == "unavailable"
