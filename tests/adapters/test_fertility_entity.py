"""Backend coverage for the opt-in fertility estimate entity.

The entity is created only when the option is on, exposes the technical state
token through its translation key, and must not leak fertility attributes onto
any pre-existing sensor. The tests drive Home Assistant through its normal
config-entry and entity-registry helpers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import date, timedelta
from typing import Any

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import (
    ATTR_CONFIDENCE_BAND,
    ATTR_ESTIMATED_FERTILE_WINDOW,
    ATTR_MARGIN_BAND,
    ATTR_MARGIN_DAYS,
    ATTR_NEXT_MARGIN_BAND,
    ATTR_PREDICTION_CONFIDENCE,
    ATTR_PREVIOUS_BAND_DAYS_AGO,
    ATTR_PREVIOUS_MARGIN_BAND,
    ATTR_USABLE_CYCLE_COUNT,
    CONF_CYCLE_LENGTH,
    CONF_ENABLE_FERTILITY_ESTIMATE,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_HISTORY_WINDOW,
    CONF_LAST_PERIOD_START,
    CONF_NOTIFICATION_OFFSET_DAYS,
    CONF_NOTIFICATION_TIME,
    CONF_PERIOD_LENGTH,
    CONF_PREDICTION_ALGORITHM,
    DEFAULT_ENABLE_FERTILITY_ESTIMATE,
    DOMAIN,
)
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator
from custom_components.cycle_tracker.sensor import (
    FertilityEstimateSensor,
)
from custom_components.cycle_tracker.sensor import (
    async_setup_entry as sensor_async_setup_entry,
)

FERTILITY_ENTITY_ID = "sensor.cycle_tracker_fertility_estimate"
FERTILITY_ATTRIBUTES = frozenset(
    {
        ATTR_ESTIMATED_FERTILE_WINDOW,
        ATTR_MARGIN_BAND,
        ATTR_MARGIN_DAYS,
        ATTR_PREDICTION_CONFIDENCE,
        ATTR_CONFIDENCE_BAND,
        ATTR_USABLE_CYCLE_COUNT,
        ATTR_PREVIOUS_MARGIN_BAND,
        ATTR_NEXT_MARGIN_BAND,
        ATTR_PREVIOUS_BAND_DAYS_AGO,
    }
)
# The other three confidence/count attributes already belong to the statistics
# and next-period sensors; only these are new to the fertility feature.
FERTILITY_ONLY_ATTRIBUTES = frozenset(
    {
        ATTR_ESTIMATED_FERTILE_WINDOW,
        ATTR_MARGIN_BAND,
        ATTR_MARGIN_DAYS,
        ATTR_PREVIOUS_MARGIN_BAND,
        ATTR_NEXT_MARGIN_BAND,
        ATTR_PREVIOUS_BAND_DAYS_AGO,
    }
)
EXISTING_SENSOR_IDS = (
    "sensor.cycle_tracker_cycle_day",
    "sensor.cycle_tracker_cycle_start_date",
    "sensor.cycle_tracker_cycle_phase",
    "sensor.cycle_tracker_next_period_date",
    "sensor.cycle_tracker_next_ovulation_date",
    "sensor.cycle_tracker_days_until_period",
    "sensor.cycle_tracker_days_until_ovulation",
    "sensor.cycle_tracker_statistics",
)


@pytest.fixture
async def enabled_coordinator(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    frozen_today: date,
) -> AsyncIterator[CycleTrackerCoordinator]:
    """Return a coordinator whose config entry opted into the estimate."""
    hass.config_entries.async_update_entry(
        config_entry, options={CONF_ENABLE_FERTILITY_ESTIMATE: True}
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    yield coordinator

    await coordinator.async_shutdown()
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


def _schema_keys(schema: vol.Schema) -> set[str]:
    return {str(marker.schema) for marker in schema.schema}


def _schema_default(schema: vol.Schema, key: str) -> Any:
    marker = next(marker for marker in schema.schema if str(marker.schema) == key)
    default = getattr(marker, "default", None)
    assert callable(default)
    return default()


def _seed_two_cycles(
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    last_start: date,
) -> None:
    """Seed two four-week cycles ending at ``last_start``."""
    for days_ago in (56, 28, 0):
        coordinator.add_period(period_row(last_start - timedelta(days=days_ago)))
    coordinator.async_update_listeners()


def _options_input(sheet_settings: dict[str, Any], *, enabled: bool) -> dict[str, Any]:
    """Build a complete submission of the options form."""
    return {
        CONF_CYCLE_LENGTH: 28,
        CONF_PERIOD_LENGTH: 5,
        CONF_PREDICTION_ALGORITHM: "weighted_moving_average",
        CONF_HISTORY_WINDOW: 6,
        CONF_ENABLE_FERTILITY_ESTIMATE: enabled,
        CONF_NOTIFICATION_OFFSET_DAYS: 2,
        CONF_ENABLE_NOTIFICATIONS: False,
        CONF_NOTIFICATION_TIME: "08:00",
        **sheet_settings,
    }


# --- constants and the coordinator resolver ----------------------------------


def test_fertility_estimate_is_disabled_by_default() -> None:
    assert DEFAULT_ENABLE_FERTILITY_ESTIMATE is False


def test_new_attribute_constants_have_stable_names() -> None:
    assert ATTR_ESTIMATED_FERTILE_WINDOW == "estimated_fertile_window"
    assert ATTR_MARGIN_BAND == "margin_band"
    assert ATTR_MARGIN_DAYS == "margin_days"


async def test_resolver_defaults_to_false_for_an_entry_without_the_key(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: CycleTrackerCoordinator,
) -> None:
    assert CONF_ENABLE_FERTILITY_ESTIMATE not in config_entry.data
    assert CONF_ENABLE_FERTILITY_ESTIMATE not in config_entry.options

    assert coordinator.get_enable_fertility_estimate() is False


async def test_resolver_reads_the_setup_data_when_no_option_is_set(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    frozen_today: date,
) -> None:
    hass.config_entries.async_update_entry(
        config_entry,
        data={**config_entry.data, CONF_ENABLE_FERTILITY_ESTIMATE: True},
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator.get_enable_fertility_estimate() is True

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_resolver_prefers_the_option_over_setup_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    frozen_today: date,
) -> None:
    hass.config_entries.async_update_entry(
        config_entry,
        data={**config_entry.data, CONF_ENABLE_FERTILITY_ESTIMATE: False},
        options={CONF_ENABLE_FERTILITY_ESTIMATE: True},
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator.get_enable_fertility_estimate() is True

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


# --- options flow -------------------------------------------------------------


async def test_options_flow_offers_the_toggle_defaulting_to_false(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: CycleTrackerCoordinator,
) -> None:
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert CONF_ENABLE_FERTILITY_ESTIMATE in _schema_keys(result["data_schema"])
    assert (
        _schema_default(result["data_schema"], CONF_ENABLE_FERTILITY_ESTIMATE) is False
    )


async def test_options_flow_shows_a_saved_toggle_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    enabled_coordinator: CycleTrackerCoordinator,
) -> None:
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert (
        _schema_default(result["data_schema"], CONF_ENABLE_FERTILITY_ESTIMATE) is True
    )


async def test_initial_setup_never_offers_the_fertility_toggle(
    hass: HomeAssistant,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["step_id"] == "user"
    assert CONF_ENABLE_FERTILITY_ESTIMATE not in _schema_keys(result["data_schema"])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CYCLE_LENGTH: 28,
            CONF_PERIOD_LENGTH: 5,
            CONF_LAST_PERIOD_START: "2026-01-01",
        },
    )
    assert result["step_id"] == "preferences"
    assert CONF_ENABLE_FERTILITY_ESTIMATE not in _schema_keys(result["data_schema"])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_PREDICTION_ALGORITHM: "weighted_moving_average",
            CONF_NOTIFICATION_OFFSET_DAYS: 2,
        },
    )
    assert result["step_id"] == "notifications"
    assert CONF_ENABLE_FERTILITY_ESTIMATE not in _schema_keys(result["data_schema"])

    hass.config_entries.flow.async_abort(result["flow_id"])


async def test_submitting_the_toggle_reloads_and_creates_the_entity(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: CycleTrackerCoordinator,
    sheet_settings: dict[str, Any],
) -> None:
    assert hass.states.get(FERTILITY_ENTITY_ID) is None

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input=_options_input(sheet_settings, enabled=True),
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert config_entry.options[CONF_ENABLE_FERTILITY_ESTIMATE] is True
    assert hass.states.get(FERTILITY_ENTITY_ID) is not None


# --- entity creation and state ------------------------------------------------


async def test_disabled_setup_creates_no_fertility_entity(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: CycleTrackerCoordinator,
) -> None:
    added: list[Any] = []
    await sensor_async_setup_entry(hass, config_entry, added.extend)

    assert not any(isinstance(entity, FertilityEstimateSensor) for entity in added)
    assert hass.states.get(FERTILITY_ENTITY_ID) is None


async def test_enabled_setup_creates_exactly_one_fertility_entity(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    enabled_coordinator: CycleTrackerCoordinator,
) -> None:
    added: list[Any] = []
    await sensor_async_setup_entry(hass, config_entry, added.extend)

    fertility_entities = [
        entity for entity in added if isinstance(entity, FertilityEstimateSensor)
    ]
    assert len(fertility_entities) == 1
    assert hass.states.get(FERTILITY_ENTITY_ID) is not None

    registry = er.async_get(hass)
    registered = [
        entry
        for entry in registry.entities.values()
        if entry.config_entry_id == config_entry.entry_id
        and entry.unique_id == f"{config_entry.entry_id}_fertility_estimate"
    ]
    assert len(registered) == 1
    assert registered[0].translation_key == "fertility_estimate"


async def test_entity_exposes_the_token_and_all_nine_attributes(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    enabled_coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    _seed_two_cycles(enabled_coordinator, period_row, date(2026, 11, 3))

    state = hass.states.get(FERTILITY_ENTITY_ID)
    assert state is not None
    assert state.state == "within_estimated_fertile_window"

    sensor = FertilityEstimateSensor(enabled_coordinator, config_entry)
    assert sensor.translation_key == "fertility_estimate"
    assert sensor.native_value == "within_estimated_fertile_window"
    attributes = sensor.extra_state_attributes
    assert set(attributes) == FERTILITY_ATTRIBUTES
    assert attributes[ATTR_ESTIMATED_FERTILE_WINDOW] == ("2026-11-12", "2026-11-17")
    assert attributes[ATTR_MARGIN_BAND] == ("2026-11-10", "2026-11-19")
    assert attributes[ATTR_MARGIN_DAYS] == 2
    assert attributes[ATTR_PREDICTION_CONFIDENCE] == pytest.approx(1 / 3)
    assert attributes[ATTR_CONFIDENCE_BAND] == "low"
    assert attributes[ATTR_USABLE_CYCLE_COUNT] == 2
    # Within the estimated window both gap edges stay absent.
    assert attributes[ATTR_PREVIOUS_MARGIN_BAND] is None
    assert attributes[ATTR_NEXT_MARGIN_BAND] is None
    assert attributes[ATTR_PREVIOUS_BAND_DAYS_AGO] is None


async def test_entity_reports_outside_and_unknown_tokens(
    hass: HomeAssistant,
    enabled_coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    unknown = hass.states.get(FERTILITY_ENTITY_ID)
    assert unknown is not None
    assert unknown.state == "unknown"

    # With this history the reference date falls between the current and the
    # next extended band.
    _seed_two_cycles(enabled_coordinator, period_row, date(2026, 10, 24))

    outside = hass.states.get(FERTILITY_ENTITY_ID)
    assert outside is not None
    assert outside.state == "outside_estimated_fertile_window"


async def test_unknown_entity_has_no_window_or_band(
    enabled_coordinator: CycleTrackerCoordinator,
    config_entry: MockConfigEntry,
) -> None:
    sensor = FertilityEstimateSensor(enabled_coordinator, config_entry)

    assert sensor.native_value == "unknown"
    assert sensor.extra_state_attributes[ATTR_ESTIMATED_FERTILE_WINDOW] is None
    assert sensor.extra_state_attributes[ATTR_MARGIN_BAND] is None
    assert sensor.extra_state_attributes[ATTR_MARGIN_DAYS] == 0
    assert sensor.extra_state_attributes[ATTR_USABLE_CYCLE_COUNT] == 0


async def test_existing_sensors_gain_no_fertility_attribute(
    hass: HomeAssistant,
    enabled_coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    _seed_two_cycles(enabled_coordinator, period_row, date(2026, 11, 3))

    for entity_id in EXISTING_SENSOR_IDS:
        state = hass.states.get(entity_id)
        assert state is not None, entity_id
        assert FERTILITY_ONLY_ATTRIBUTES.isdisjoint(state.attributes), entity_id


async def test_enabling_the_option_creates_the_entity_on_reload(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: CycleTrackerCoordinator,
) -> None:
    assert hass.states.get(FERTILITY_ENTITY_ID) is None

    hass.config_entries.async_update_entry(
        config_entry, options={CONF_ENABLE_FERTILITY_ESTIMATE: True}
    )
    await hass.async_block_till_done()

    assert coordinator.get_enable_fertility_estimate() is True
    assert hass.states.get(FERTILITY_ENTITY_ID) is not None
