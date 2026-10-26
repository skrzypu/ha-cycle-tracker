"""Unit tests for the Cycle Tracker service handlers."""

from datetime import date
from types import SimpleNamespace
from typing import Any, Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol

from custom_components.cycle_tracker.const import (
    DOMAIN,
    SERVICE_LOG_END,
    SERVICE_LOG_START,
)
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator
from custom_components.cycle_tracker.services import (
    SERVICE_LOG_END_SCHEMA,
    SERVICE_LOG_START_SCHEMA,
    async_setup_services,
    async_unload_services,
)

Handler = Callable[[Any], Awaitable[dict[str, Any]]]


@pytest.fixture
def coordinator() -> CycleTrackerCoordinator:
    """Coordinator with storage mocked out and empty data."""
    store = AsyncMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    with patch("custom_components.cycle_tracker.coordinator.Store", return_value=store):
        coord = CycleTrackerCoordinator(MagicMock(), MagicMock())
    coord.store = store
    coord._data = {"periods": []}
    return coord


@pytest.fixture
def fake_hass(coordinator: CycleTrackerCoordinator) -> MagicMock:
    """Fake hass exposing the coordinator under DOMAIN."""
    hass = MagicMock()
    hass.data = {DOMAIN: {"test_entry_id": coordinator}}
    hass.services = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    return hass


def _make_call(call_data: dict[str, Any]) -> Any:
    """Build a fake ServiceCall with controllable data and config entry."""
    call: Any = SimpleNamespace(
        data=call_data,
        config_entry=SimpleNamespace(entry_id="test_entry_id"),
    )
    return call


async def _registered_handlers(hass: MagicMock) -> dict[str, Handler]:
    """Register the services and capture the handlers that were registered."""
    await async_setup_services(hass)
    return {
        call.args[1]: call.args[2]
        for call in hass.services.async_register.call_args_list
    }


class TestLogStart:
    """Tests for the log_start service handler."""

    @pytest.mark.asyncio
    async def test_log_start_stores_period(self, fake_hass, coordinator):
        """A valid call stores a period and reports success."""
        handlers = await _registered_handlers(fake_hass)
        call = _make_call({"date": date(2024, 2, 1), "flow_intensity": "heavy"})

        response = await handlers[SERVICE_LOG_START](call)

        assert response["success"] is True
        assert "2024-02-01" in response["message"]
        assert coordinator.get_periods() == [
            {
                "start_date": "2024-02-01",
                "end_date": "2024-02-01",
                "flow_intensity": "heavy",
            }
        ]
        coordinator.store.async_save.assert_awaited_once_with(coordinator._data)

    @pytest.mark.asyncio
    async def test_log_start_same_day_updates_existing(self, fake_hass, coordinator):
        """Logging the same day twice updates instead of duplicating."""
        coordinator._data = {
            "periods": [
                {
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-01",
                    "flow_intensity": "light",
                }
            ]
        }
        handlers = await _registered_handlers(fake_hass)
        call = _make_call({"date": date(2024, 1, 1), "flow_intensity": "heavy"})

        response = await handlers[SERVICE_LOG_START](call)

        assert response["success"] is True
        assert len(coordinator.get_periods()) == 1
        assert coordinator.get_periods()[0]["flow_intensity"] == "heavy"


class TestLogStartSchema:
    """Tests for the log_start service schema."""

    def test_schema_accepts_valid_data(self):
        """Valid data passes validation and flow_intensity defaults."""
        validated = SERVICE_LOG_START_SCHEMA({"date": date(2024, 2, 1)})

        assert validated["date"] == date(2024, 2, 1)
        assert validated["flow_intensity"] == "medium"

    def test_schema_rejects_invalid_flow_intensity(self):
        """An unknown flow_intensity is rejected."""
        with pytest.raises(vol.Invalid):
            SERVICE_LOG_START_SCHEMA(
                {"date": date(2024, 2, 1), "flow_intensity": "extreme"}
            )

    def test_log_end_schema_requires_date(self):
        """log_end rejects calls without a date."""
        with pytest.raises(vol.Invalid):
            SERVICE_LOG_END_SCHEMA({})


class TestLogEnd:
    """Tests for the log_end service handler."""

    @pytest.mark.asyncio
    async def test_log_end_sets_end_date(self, fake_hass, coordinator):
        """Ending an open period stores the end date."""
        coordinator._data = {
            "periods": [
                {
                    "start_date": "2024-02-01",
                    "end_date": "2024-02-01",
                    "flow_intensity": "medium",
                }
            ]
        }
        handlers = await _registered_handlers(fake_hass)
        call = _make_call({"date": date(2024, 2, 5)})

        response = await handlers[SERVICE_LOG_END](call)

        assert response["success"] is True
        assert coordinator.get_periods()[0]["end_date"] == "2024-02-05"
        coordinator.store.async_save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_log_end_without_period_changes_nothing(self, fake_hass, coordinator):
        """Ending with no recorded period fails without mutating data."""
        handlers = await _registered_handlers(fake_hass)
        call = _make_call({"date": date(2024, 2, 5)})

        response = await handlers[SERVICE_LOG_END](call)

        assert response["success"] is False
        assert "No period started to end" == response["message"]
        assert coordinator.get_periods() == []
        coordinator.store.async_save.assert_not_awaited()


class TestServiceLifecycle:
    """Tests for service registration and teardown."""

    @pytest.mark.asyncio
    async def test_setup_registers_both_services(self, fake_hass):
        """Both services are registered on setup."""
        await async_setup_services(fake_hass)

        registered = {
            call.args[1] for call in fake_hass.services.async_register.call_args_list
        }
        assert registered == {SERVICE_LOG_START, SERVICE_LOG_END}

    @pytest.mark.asyncio
    async def test_unload_removes_both_services(self, fake_hass):
        """Unloading removes both registered services."""
        await async_unload_services(fake_hass)

        removed = {call.args for call in fake_hass.services.async_remove.call_args_list}
        assert removed == {(DOMAIN, SERVICE_LOG_START), (DOMAIN, SERVICE_LOG_END)}

    @pytest.mark.asyncio
    async def test_setup_entry_registers_unload_callback(self, fake_hass):
        """async_setup_entry registers service teardown via async_on_unload."""
        from custom_components.cycle_tracker import async_setup_entry

        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.async_on_unload = MagicMock()
        coordinator = AsyncMock()
        coordinator.async_config_entry_first_refresh = AsyncMock()

        with patch(
            "custom_components.cycle_tracker.CycleTrackerCoordinator",
            return_value=coordinator,
        ):
            assert await async_setup_entry(fake_hass, entry) is True

        # Should be called twice: once for update listener, once for service teardown
        assert entry.async_on_unload.call_count == 2
        # Verify the second call is the service unload callback
        unload_callback = entry.async_on_unload.call_args_list[1].args[0]

        fake_hass.services.async_remove.reset_mock()
        await unload_callback()

        removed = {call.args for call in fake_hass.services.async_remove.call_args_list}
        assert removed == {(DOMAIN, SERVICE_LOG_START), (DOMAIN, SERVICE_LOG_END)}
