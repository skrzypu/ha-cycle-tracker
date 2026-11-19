"""Tests for the Cycle Tracker logging services.

The services are driven through the Home Assistant service registry, because
that is where the target is merged into the service data and the schema runs;
a stand-in call object would never exercise either step.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import (
    CONF_CYCLE_LENGTH,
    CONF_LAST_PERIOD_START,
    CONF_PERIOD_LENGTH,
    CONF_PREDICTION_ALGORITHM,
    DOMAIN,
    SERVICE_LOG_END,
    SERVICE_LOG_START,
)
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator

CYCLE_DAY_ENTITY = "sensor.cycle_tracker_cycle_day"
FOREIGN_ENTITY = "light.kitchen"


def _entry_data() -> dict[str, Any]:
    """Return the config data both entries in these tests use."""
    return {
        CONF_CYCLE_LENGTH: 28,
        CONF_PERIOD_LENGTH: 5,
        CONF_LAST_PERIOD_START: "2026-01-01",
        CONF_PREDICTION_ALGORITHM: "weighted_moving_average",
    }


async def _call_service(
    hass: HomeAssistant,
    service: str,
    data: dict[str, Any],
    target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call a logging service and return its response."""
    response = await hass.services.async_call(
        DOMAIN,
        service,
        data,
        blocking=True,
        return_response=True,
        target=target,
    )
    assert response is not None
    return response


async def test_no_service_is_registered_for_the_history_window(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
) -> None:
    """The window is settings-only: no third service is added to the domain."""
    assert set(hass.services.async_services()[DOMAIN]) == {
        SERVICE_LOG_START,
        SERVICE_LOG_END,
    }


async def test_log_start_without_target_records_open_period(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    frozen_today: date,
    period_row,
) -> None:
    """A targetless call applies to the only entry and leaves the period open."""
    coordinator.add_period(period_row(frozen_today - timedelta(days=60), length=3))
    coordinator.async_set_updated_data(coordinator._data)
    closed_average = coordinator.snapshot.statistics.average_period_length
    assert closed_average == 3.0

    start = frozen_today - timedelta(days=3)
    response = await _call_service(hass, SERVICE_LOG_START, {"date": start})

    assert response["success"] is True
    periods = coordinator.get_periods()
    assert len(periods) == 2
    assert periods[0] == period_row(frozen_today - timedelta(days=60), length=3)
    assert periods[1]["start_date"] == start.isoformat()
    assert periods[1]["end_date"] == start.isoformat()
    assert periods[1]["flow_intensity"] == "medium"
    assert UUID(periods[1]["period_id"])
    # The open period adds a recorded period but no period length.
    assert coordinator.snapshot.statistics.total_cycles_tracked == 2
    assert coordinator.snapshot.statistics.average_period_length == closed_average


async def test_log_start_and_log_end_with_entity_target(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    frozen_today: date,
) -> None:
    """An entity target selects the entry that owns the entity."""
    start = frozen_today - timedelta(days=10)
    response = await _call_service(
        hass,
        SERVICE_LOG_START,
        {"date": start, "flow_intensity": "light"},
        target={"entity_id": CYCLE_DAY_ENTITY},
    )

    assert response["success"] is True
    opened = coordinator.get_periods()[-1]
    assert opened["start_date"] == start.isoformat()
    assert opened["end_date"] == start.isoformat()
    assert opened["flow_intensity"] == "light"
    assert UUID(opened["period_id"])
    assert coordinator.snapshot.statistics.average_period_length == 5.0

    end = start + timedelta(days=3)
    response = await _call_service(
        hass,
        SERVICE_LOG_END,
        {"date": end},
        target={"entity_id": CYCLE_DAY_ENTITY},
    )

    assert response["success"] is True
    periods = coordinator.get_periods()
    assert len(periods) == 1
    assert periods[0]["period_id"] == opened["period_id"]
    assert periods[0]["start_date"] == start.isoformat()
    assert periods[0]["end_date"] == end.isoformat()
    assert periods[0]["flow_intensity"] == "light"
    assert periods[0]["notes"] is None
    assert isinstance(periods[0]["updated_at"], str)
    # Four bleeding days now count instead of the configured five.
    assert coordinator.snapshot.statistics.average_period_length == 4.0


async def test_log_start_rejects_foreign_target(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    frozen_today: date,
) -> None:
    """A target that holds no entity of the integration records nothing."""
    hass.states.async_set(FOREIGN_ENTITY, "on")

    with pytest.raises(ServiceValidationError):
        await _call_service(
            hass,
            SERVICE_LOG_START,
            {"date": frozen_today},
            target={"entity_id": FOREIGN_ENTITY},
        )

    assert coordinator.get_periods() == []


async def test_log_start_without_target_rejects_ambiguous_entries(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    frozen_today: date,
) -> None:
    """Two entries make a targetless call ambiguous, so nothing is written."""
    second_entry = MockConfigEntry(
        domain=DOMAIN,
        data=_entry_data(),
        unique_id="second-cycle-tracker",
        title="Cycle Tracker",
    )
    second_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second_entry.entry_id)
    await hass.async_block_till_done()

    second_coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][
        second_entry.entry_id
    ]
    try:
        with pytest.raises(ServiceValidationError):
            await _call_service(hass, SERVICE_LOG_START, {"date": frozen_today})

        assert coordinator.get_periods() == []
        assert second_coordinator.get_periods() == []
    finally:
        await second_coordinator.async_shutdown()
        assert await hass.config_entries.async_unload(second_entry.entry_id)
        await hass.async_block_till_done()


async def test_log_end_before_start_is_refused(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    sheet_emulator: Any,
    frozen_today: date,
) -> None:
    """An end date before the start is refused and the sheet row survives."""
    start = frozen_today - timedelta(days=5)
    await _call_service(hass, SERVICE_LOG_START, {"date": start})
    before = [dict(row) for row in coordinator.get_periods()]
    before_rows = sheet_emulator.rows

    response = await _call_service(
        hass, SERVICE_LOG_END, {"date": start - timedelta(days=1)}
    )

    assert response["success"] is False
    assert "message" in response
    assert coordinator.get_periods() == before
    assert sheet_emulator.rows == before_rows


async def test_log_end_is_refused_without_an_open_period(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    frozen_today: date,
) -> None:
    """Neither a missing nor an already closed period can be ended again."""
    start = frozen_today - timedelta(days=4)

    response = await _call_service(hass, SERVICE_LOG_END, {"date": start})
    assert response["success"] is False
    assert coordinator.get_periods() == []

    await _call_service(hass, SERVICE_LOG_START, {"date": start})
    await _call_service(hass, SERVICE_LOG_END, {"date": start + timedelta(days=2)})
    closed = [dict(row) for row in coordinator.get_periods()]

    response = await _call_service(
        hass, SERVICE_LOG_END, {"date": start + timedelta(days=3)}
    )

    assert response["success"] is False
    assert coordinator.get_periods() == closed


async def test_logged_period_id_survives_a_restart(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    frozen_today: date,
) -> None:
    """A period id created by log_start is still there after a coordinator reload."""
    start = frozen_today - timedelta(days=4)
    await _call_service(hass, SERVICE_LOG_START, {"date": start})
    logged_id = coordinator.get_periods()[-1]["period_id"]

    await coordinator.async_refresh()

    assert coordinator.get_periods()[-1]["period_id"] == logged_id
