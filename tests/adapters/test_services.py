"""Tests for the Cycle Tracker logging services.

The services are driven through the Home Assistant service registry, because
that is where the target is merged into the service data and the schema runs;
a stand-in call object would never exercise either step.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
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
    SERVICE_REFRESH,
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


async def test_only_the_expected_services_are_registered(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
) -> None:
    """The domain exposes exactly log_start, log_end and refresh."""
    assert set(hass.services.async_services()[DOMAIN]) == {
        SERVICE_LOG_START,
        SERVICE_LOG_END,
        SERVICE_REFRESH,
    }


async def test_refresh_without_target_rereads_the_sheet(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    sheet_reads: Callable[[CycleTrackerCoordinator], dict[str, int]],
) -> None:
    """With one entry, a targetless refresh performs exactly one sheet read."""
    reads = sheet_reads(coordinator)

    await hass.services.async_call(DOMAIN, SERVICE_REFRESH, {}, blocking=True)
    await hass.async_block_till_done()

    assert reads["reads"] == 1


async def test_refresh_with_entity_target_rereads_the_sheet(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    sheet_reads: Callable[[CycleTrackerCoordinator], dict[str, int]],
) -> None:
    """A Cycle Tracker entity target selects the entry to re-read."""
    reads = sheet_reads(coordinator)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH,
        {},
        target={"entity_id": CYCLE_DAY_ENTITY},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert reads["reads"] == 1


async def test_refresh_rejects_foreign_target(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    sheet_reads: Callable[[CycleTrackerCoordinator], dict[str, int]],
) -> None:
    """A target with no Cycle Tracker entity is rejected without a read."""
    hass.states.async_set(FOREIGN_ENTITY, "on")
    reads = sheet_reads(coordinator)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH,
            {},
            target={"entity_id": FOREIGN_ENTITY},
            blocking=True,
        )
    await hass.async_block_till_done()

    assert reads["reads"] == 0


async def test_refresh_without_target_rejects_ambiguous_entries(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    sheet_settings: dict[str, Any],
    sheet_reads: Callable[[CycleTrackerCoordinator], dict[str, int]],
) -> None:
    """Two configured entries make a targetless refresh ambiguous."""
    second_entry = MockConfigEntry(
        domain=DOMAIN,
        data={**_entry_data(), **sheet_settings},
        unique_id="second-cycle-tracker",
        title="Cycle Tracker",
    )
    second_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second_entry.entry_id)
    await hass.async_block_till_done()

    second_coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][
        second_entry.entry_id
    ]
    reads = sheet_reads(coordinator)
    second_reads = sheet_reads(second_coordinator)
    try:
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(DOMAIN, SERVICE_REFRESH, {}, blocking=True)
        await hass.async_block_till_done()

        assert reads["reads"] == 0
        assert second_reads["reads"] == 0
    finally:
        await second_coordinator.async_shutdown()
        assert await hass.config_entries.async_unload(second_entry.entry_id)
        await hass.async_block_till_done()


async def test_unload_removes_the_refresh_service(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Unload unregisters refresh along with the logging services."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert SERVICE_REFRESH in hass.services.async_services()[DOMAIN]

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert SERVICE_REFRESH not in hass.services.async_services().get(DOMAIN, {})


async def test_log_start_rereads_the_sheet_and_publishes_once(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    sheet_reads: Callable[[CycleTrackerCoordinator], dict[str, int]],
    frozen_today: date,
) -> None:
    """A successful start write re-reads the sheet and notifies once."""
    reads = sheet_reads(coordinator)
    listener = Mock()
    unsub_listener = coordinator.async_add_listener(listener)

    response = await _call_service(hass, SERVICE_LOG_START, {"date": frozen_today})
    await hass.async_block_till_done()

    assert response["success"] is True
    assert reads["reads"] == 1
    listener.assert_called_once()
    unsub_listener()


async def test_log_end_rereads_the_sheet_and_publishes_once(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    sheet_emulator: Any,
    sheet_reads: Callable[[CycleTrackerCoordinator], dict[str, int]],
    frozen_today: date,
) -> None:
    """A successful end write re-reads the sheet and notifies once."""
    start = frozen_today - timedelta(days=5)
    # Seed the open row in the sheet and load it directly: a preceding service
    # write would leave the coordinator's 10s refresh debouncer armed.
    sheet_emulator.seed(
        [
            [
                "12345678-1234-5678-1234-567812345678",
                start.isoformat(),
                start.isoformat(),  # end == start means still open
                "medium",
                "",
                "",
            ]
        ]
    )
    await coordinator.async_refresh()

    reads = sheet_reads(coordinator)
    listener = Mock()
    unsub_listener = coordinator.async_add_listener(listener)

    response = await _call_service(
        hass, SERVICE_LOG_END, {"date": start + timedelta(days=3)}
    )
    await hass.async_block_till_done()

    assert response["success"] is True
    assert reads["reads"] == 1
    listener.assert_called_once()
    unsub_listener()


async def test_failed_write_requests_no_reread(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    sheet_reads: Callable[[CycleTrackerCoordinator], dict[str, int]],
    frozen_today: date,
) -> None:
    """A refused end leaves the sheet unread and last_sync unchanged."""
    reads = sheet_reads(coordinator)
    sync_before = coordinator.last_sync

    response = await _call_service(hass, SERVICE_LOG_END, {"date": frozen_today})
    await hass.async_block_till_done()

    assert response["success"] is False
    assert reads["reads"] == 0
    assert coordinator.last_sync == sync_before


async def test_last_sync_updates_only_after_a_successful_reread(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    sheet_emulator: Any,
    freezer: Any,
    frozen_today: date,
) -> None:
    """A failed re-read after a write keeps the previous last_sync."""
    initial_sync = coordinator.last_sync
    assert initial_sync is not None
    freezer.move_to("2026-11-13 12:05:00")

    with patch.object(
        coordinator._repo, "read_all", AsyncMock(side_effect=RuntimeError("boom"))
    ):
        response = await _call_service(hass, SERVICE_LOG_START, {"date": frozen_today})
        await hass.async_block_till_done()

    assert response["success"] is True
    assert any(row[1] == frozen_today.isoformat() for row in sheet_emulator.rows)
    assert coordinator.last_sync == initial_sync

    # A direct successful re-read (the same path the service requests) updates
    # the timestamp; the debouncer would defer a second service request here.
    await coordinator.async_refresh()

    assert coordinator.last_sync is not None
    assert coordinator.last_sync > initial_sync


async def test_log_start_without_target_records_open_period(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    sheet_emulator: Any,
    frozen_today: date,
    period_row,
) -> None:
    """A targetless call applies to the only entry and leaves the period open.

    History is seeded in the sheet, not only in memory, because a successful
    write now re-reads the sheet as its source of truth.
    """
    closed = period_row(frozen_today - timedelta(days=60), length=3)
    sheet_emulator.seed(
        [
            [
                closed["period_id"],
                closed["start_date"],
                closed["end_date"],
                closed["flow_intensity"],
                "",
                "",
            ]
        ]
    )
    await coordinator.async_refresh()
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
