"""Home Assistant fixtures shared by the adapter and end-to-end suites.

The domain tests keep their own conftest: they deliberately stay free of the
Home Assistant harness (ADR-0005), so nothing here imports Home Assistant at
module scope. ``config_entry`` is the single entry both suites build on, which
keeps the settings they exercise from drifting apart, and ``coordinator``
remains the adapter-level handle while the end-to-end tests go through the
service registry instead.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator

# `pytest_homeassistant_custom_component` is registered through its `pytest11`
# entry point, so the Home Assistant fixtures are already available here; pytest
# rejects a `pytest_plugins` declaration outside the rootdir conftest.

FROZEN_TODAY = date(2026, 11, 13)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request: pytest.FixtureRequest) -> Iterator[None]:
    """Let Home Assistant load the custom integration under test.

    Only tests that use ``hass`` opt in, so the framework-free domain tests keep
    running without requesting a Home Assistant fixture.
    """
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")
    yield


@pytest.fixture
def frozen_today(freezer) -> date:
    """Pin the wall clock so the snapshot reference date is deterministic."""
    freezer.move_to("2026-11-13 12:00:00")
    return FROZEN_TODAY


@pytest.fixture
def config_entry_data() -> dict[str, Any]:
    """Return the settings of the shared entry.

    A test module can override this fixture to exercise an entry with different
    or missing settings, which is how the shipped defaults get covered.
    """
    from custom_components.cycle_tracker.const import (
        CONF_CYCLE_LENGTH,
        CONF_LAST_PERIOD_START,
        CONF_PERIOD_LENGTH,
        CONF_PREDICTION_ALGORITHM,
    )

    return {
        CONF_CYCLE_LENGTH: 28,
        CONF_PERIOD_LENGTH: 5,
        CONF_LAST_PERIOD_START: "2026-01-01",
        CONF_PREDICTION_ALGORITHM: "weighted_moving_average",
    }


@pytest.fixture
def config_entry(
    hass: HomeAssistant, config_entry_data: dict[str, Any]
) -> MockConfigEntry:
    """Return a registered config entry carrying ``config_entry_data``."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.cycle_tracker.const import DOMAIN

    entry = MockConfigEntry(domain=DOMAIN, data=config_entry_data)
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def coordinator(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    frozen_today: date,
) -> AsyncIterator[CycleTrackerCoordinator]:
    """Set up the integration and return its coordinator."""
    from custom_components.cycle_tracker.const import DOMAIN

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
