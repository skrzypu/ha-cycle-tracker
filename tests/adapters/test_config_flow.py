"""Tests for the options dialog and the settings it edits.

Home Assistant starts an options flow through ``OptionsFlowManager``, which is
also the only place where ``OptionsFlow.config_entry`` becomes available, so the
tests drive the dialog through ``hass.config_entries.options`` instead of
constructing the flow themselves.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import (
    CONF_CYCLE_LENGTH,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_LAST_PERIOD_START,
    CONF_NOTIFICATION_OFFSET_DAYS,
    CONF_NOTIFICATION_TIME,
    CONF_PERIOD_LENGTH,
    CONF_PREDICTION_ALGORITHM,
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_NOTIFICATION_OFFSET_DAYS,
    DEFAULT_NOTIFICATION_TIME,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator

CHANGED_CYCLE_LENGTH = 31
CHANGED_PERIOD_LENGTH = 6
STORED_CYCLE_LENGTH = 99


def _entry_data() -> dict[str, Any]:
    """Return the setup data the shared config entry fixture records."""
    return {
        CONF_CYCLE_LENGTH: 28,
        CONF_PERIOD_LENGTH: 5,
        CONF_LAST_PERIOD_START: "2026-01-01",
        CONF_PREDICTION_ALGORITHM: "weighted_moving_average",
    }


def _options_input(cycle_length: int) -> dict[str, Any]:
    """Return a complete submission of the options form."""
    return {
        CONF_CYCLE_LENGTH: cycle_length,
        CONF_PERIOD_LENGTH: CHANGED_PERIOD_LENGTH,
        CONF_PREDICTION_ALGORITHM: "arithmetic_mean",
        CONF_NOTIFICATION_OFFSET_DAYS: 3,
        CONF_ENABLE_NOTIFICATIONS: True,
        CONF_NOTIFICATION_TIME: "09:30",
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
) -> None:
    """The dialog opens as a form showing the effective settings."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert _form_defaults(result["data_schema"]) == {
        CONF_CYCLE_LENGTH: _entry_data()[CONF_CYCLE_LENGTH],
        CONF_PERIOD_LENGTH: _entry_data()[CONF_PERIOD_LENGTH],
        CONF_PREDICTION_ALGORITHM: _entry_data()[CONF_PREDICTION_ALGORITHM],
        CONF_NOTIFICATION_OFFSET_DAYS: DEFAULT_NOTIFICATION_OFFSET_DAYS,
        CONF_ENABLE_NOTIFICATIONS: DEFAULT_ENABLE_NOTIFICATIONS,
        CONF_NOTIFICATION_TIME: DEFAULT_NOTIFICATION_TIME,
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


async def test_saved_options_reach_the_coordinator(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: CycleTrackerCoordinator,
) -> None:
    """Submitting the dialog stores the option and the reload reads it."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=_options_input(CHANGED_CYCLE_LENGTH)
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_CYCLE_LENGTH] == CHANGED_CYCLE_LENGTH

    await hass.async_block_till_done()

    reloaded: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert reloaded.get_cycle_length() == CHANGED_CYCLE_LENGTH
    assert reloaded.get_period_length() == CHANGED_PERIOD_LENGTH
    assert reloaded.get_prediction_config().cycle_length == CHANGED_CYCLE_LENGTH
    # Below two usable cycles the statistics fall back to the configured length.
    assert reloaded.snapshot.statistics.average_cycle_length == float(
        CHANGED_CYCLE_LENGTH
    )


async def test_a_stored_setting_copy_does_not_override_the_entry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Stored settings are dropped instead of shadowing the config entry."""
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_save({"periods": [], CONF_CYCLE_LENGTH: STORED_CYCLE_LENGTH})
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator.get_cycle_length() == _entry_data()[CONF_CYCLE_LENGTH]
    assert coordinator.get_cycle_length() != STORED_CYCLE_LENGTH
    assert set(coordinator.data) == {"periods"}

    await coordinator.async_save_data()
    assert await store.async_load() == {"periods": []}

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
