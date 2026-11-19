"""Tests for the period-open binary sensor reading the prediction snapshot."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from custom_components.cycle_tracker.binary_sensor import PeriodOpenBinarySensor
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator

PERIOD_OPEN = "binary_sensor.cycle_tracker_period_open"


async def test_period_open_binary_sensor_is_off_without_an_open_period(
    hass,
    coordinator: CycleTrackerCoordinator,
) -> None:
    """With no recorded period the binary sensor is off."""
    state = hass.states.get(PERIOD_OPEN)
    assert state is not None
    assert state.state == "off"


async def test_period_open_binary_sensor_is_on_while_a_period_is_open(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """A recorded period with no end date turns the binary sensor on."""
    row = period_row(frozen_today)
    row["end_date"] = None
    coordinator.add_period(row)
    coordinator.async_update_listeners()

    state = hass.states.get(PERIOD_OPEN)
    assert state is not None
    assert state.state == "on"


async def test_period_open_binary_sensor_mirrors_coordinator_availability(
    hass,
    config_entry,
) -> None:
    """An unavailable coordinator makes the binary sensor unavailable.

    For a non-remote repository ``coordinator.available`` returns
    ``last_update_success``, so flipping that flag drives the entity.
    """
    from custom_components.cycle_tracker.repository import LocalStoreRepository

    coordinator = CycleTrackerCoordinator(
        hass, config_entry, repo=LocalStoreRepository(hass)
    )
    entity = PeriodOpenBinarySensor(coordinator, config_entry)

    assert entity.available is True

    coordinator.last_update_success = False

    assert entity.available is False
