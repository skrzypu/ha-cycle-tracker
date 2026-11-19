"""Tests for the options dialog and the settings it edits.

Home Assistant starts an options flow through ``OptionsFlowManager``, which is
also the only place where ``OptionsFlow.config_entry`` becomes available, so the
tests drive the dialog through ``hass.config_entries.options`` instead of
constructing the flow themselves.
"""

from __future__ import annotations

from typing import Any

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import (
    CONF_CYCLE_LENGTH,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_HISTORY_WINDOW,
    CONF_LAST_PERIOD_START,
    CONF_NOTIFICATION_OFFSET_DAYS,
    CONF_NOTIFICATION_TIME,
    CONF_PERIOD_LENGTH,
    CONF_POLL_INTERVAL,
    CONF_PREDICTION_ALGORITHM,
    CONF_SERVICE_ACCOUNT_FILE,
    CONF_SPREADSHEET_ID,
    CONF_WORKSHEET,
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_NOTIFICATION_OFFSET_DAYS,
    DEFAULT_NOTIFICATION_TIME,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_KEY_SYNC_CACHE,
    STORAGE_VERSION,
    STORAGE_VERSION_SYNC_CACHE,
)
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator
from custom_components.cycle_tracker.domain.ports import DEFAULT_HISTORY_WINDOW

CHANGED_CYCLE_LENGTH = 31
CHANGED_HISTORY_WINDOW = 18
CHANGED_PERIOD_LENGTH = 6
STORED_CYCLE_LENGTH = 99


def _entry_data(sheet_settings: dict[str, Any]) -> dict[str, Any]:
    """Return the setup data the shared config entry fixture records."""
    return {
        CONF_CYCLE_LENGTH: 28,
        CONF_PERIOD_LENGTH: 5,
        CONF_LAST_PERIOD_START: "2026-01-01",
        CONF_PREDICTION_ALGORITHM: "weighted_moving_average",
        **sheet_settings,
    }


def _options_input(cycle_length: int, sheet_settings: dict[str, Any]) -> dict[str, Any]:
    """Return a complete submission of the options form."""
    return {
        CONF_CYCLE_LENGTH: cycle_length,
        CONF_PERIOD_LENGTH: CHANGED_PERIOD_LENGTH,
        CONF_PREDICTION_ALGORITHM: "arithmetic_mean",
        CONF_NOTIFICATION_OFFSET_DAYS: 3,
        CONF_ENABLE_NOTIFICATIONS: True,
        CONF_NOTIFICATION_TIME: "09:30",
        CONF_HISTORY_WINDOW: CHANGED_HISTORY_WINDOW,
        **sheet_settings,
    }


def _form_defaults(schema: vol.Schema) -> dict[str, Any]:
    """Return the value each field of a form is pre-filled with."""
    defaults: dict[str, Any] = {}
    for marker in schema.schema:
        factory = getattr(marker, "default", None)
        assert callable(factory), f"form field {marker} has no default"
        defaults[str(marker.schema)] = factory()
    return defaults


async def test_options_dialog_opens_prefilled_with_the_values_in_force(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: CycleTrackerCoordinator,
    sheet_settings: dict[str, Any],
) -> None:
    """The dialog opens as a form showing the effective settings."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    entry_data = _entry_data(sheet_settings)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert _form_defaults(result["data_schema"]) == {
        CONF_CYCLE_LENGTH: entry_data[CONF_CYCLE_LENGTH],
        CONF_PERIOD_LENGTH: entry_data[CONF_PERIOD_LENGTH],
        CONF_PREDICTION_ALGORITHM: entry_data[CONF_PREDICTION_ALGORITHM],
        CONF_NOTIFICATION_OFFSET_DAYS: DEFAULT_NOTIFICATION_OFFSET_DAYS,
        CONF_ENABLE_NOTIFICATIONS: DEFAULT_ENABLE_NOTIFICATIONS,
        CONF_NOTIFICATION_TIME: DEFAULT_NOTIFICATION_TIME,
        CONF_HISTORY_WINDOW: DEFAULT_HISTORY_WINDOW,
        CONF_SPREADSHEET_ID: entry_data[CONF_SPREADSHEET_ID],
        CONF_WORKSHEET: entry_data[CONF_WORKSHEET],
        CONF_SERVICE_ACCOUNT_FILE: entry_data[CONF_SERVICE_ACCOUNT_FILE],
        CONF_POLL_INTERVAL: entry_data[CONF_POLL_INTERVAL],
    }


async def test_options_dialog_prefers_saved_options_over_setup_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Reopening the dialog shows the option in force, not the setup value."""
    hass.config_entries.async_update_entry(
        config_entry, options={CONF_CYCLE_LENGTH: CHANGED_CYCLE_LENGTH}
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert (
        _form_defaults(result["data_schema"])[CONF_CYCLE_LENGTH] == CHANGED_CYCLE_LENGTH
    )

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_options_dialog_shows_the_saved_history_window(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """A saved window wins over the 6 an entry with no stored value resolves to."""
    hass.config_entries.async_update_entry(
        config_entry, options={CONF_HISTORY_WINDOW: CHANGED_HISTORY_WINDOW}
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert (
        _form_defaults(result["data_schema"])[CONF_HISTORY_WINDOW]
        == CHANGED_HISTORY_WINDOW
    )

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize("window", [5, 25])
async def test_options_dialog_rejects_an_out_of_range_history_window(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    sheet_settings: dict[str, Any],
    window: int,
) -> None:
    """The NumberSelector rejects 5 and 25 before the flow step runs."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    submission = {
        **_options_input(CHANGED_CYCLE_LENGTH, sheet_settings),
        CONF_HISTORY_WINDOW: window,
    }
    with pytest.raises(vol.Invalid):
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=submission
        )

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_saved_options_reach_the_coordinator(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: CycleTrackerCoordinator,
    sheet_settings: dict[str, Any],
) -> None:
    """Submitting the dialog stores the option and the reload reads it."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input=_options_input(CHANGED_CYCLE_LENGTH, sheet_settings),
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_CYCLE_LENGTH] == CHANGED_CYCLE_LENGTH

    await hass.async_block_till_done()

    reloaded: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert reloaded.get_cycle_length() == CHANGED_CYCLE_LENGTH
    assert reloaded.get_period_length() == CHANGED_PERIOD_LENGTH
    assert reloaded.get_history_window() == CHANGED_HISTORY_WINDOW
    assert reloaded.get_prediction_config().cycle_length == CHANGED_CYCLE_LENGTH
    assert reloaded.get_prediction_config().history_window == CHANGED_HISTORY_WINDOW
    # Below two usable cycles the statistics fall back to the configured length.
    assert reloaded.snapshot.statistics.average_cycle_length == float(
        CHANGED_CYCLE_LENGTH
    )


async def test_a_stored_setting_copy_does_not_override_the_entry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    config_entry_data: dict[str, Any],
) -> None:
    """A legacy settings copy is read only by the import, never by the coordinator.

    The coordinator keeps recorded periods in the user's sheet, so local storage
    only holds the sheet-sync cache. A stored legacy payload with an old cycle
    length must leave the config entry's value in force and must leave the cache
    limited to the sheet-sync fields.
    """
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_save({"periods": [], CONF_CYCLE_LENGTH: STORED_CYCLE_LENGTH})
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator.get_cycle_length() == config_entry_data[CONF_CYCLE_LENGTH]
    assert coordinator.get_cycle_length() != STORED_CYCLE_LENGTH
    assert coordinator.data == {"periods": []}

    await coordinator.async_save_data()

    cache_store: Store[dict[str, Any]] = Store(
        hass, STORAGE_VERSION_SYNC_CACHE, STORAGE_KEY_SYNC_CACHE
    )
    cached = await cache_store.async_load()
    assert isinstance(cached, dict)
    assert set(cached) == {
        "periods",
        "last_sync",
        "last_error",
        "consecutive_failures",
    }
    assert cached["periods"] == []
    assert CONF_CYCLE_LENGTH not in cached

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
