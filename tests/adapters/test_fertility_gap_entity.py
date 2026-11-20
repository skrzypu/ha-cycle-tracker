"""Entity surface for both fertility gap edges (change fertility-gap-both-bands).

The sensor must serialize the two new domain fields as inclusive ISO pairs (or
``None``) without changing any existing attribute, and no other sensor may gain
the new attributes. Stub cases pin the exact serialization; the last tests check
the real coordinator → sensor wiring.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
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
    DOMAIN,
)
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator
from custom_components.cycle_tracker.domain.fertility import (
    FertilityEstimate,
    FertilityState,
)
from custom_components.cycle_tracker.domain.models import ConfidenceBand
from custom_components.cycle_tracker.sensor import FertilityEstimateSensor

NEW_ATTRIBUTES = frozenset({ATTR_PREVIOUS_MARGIN_BAND, ATTR_NEXT_MARGIN_BAND})
ALL_ATTRIBUTES = frozenset(
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


class _StubCoordinator:
    """Only the ``snapshot`` surface the fertility sensor reads."""

    def __init__(self, estimate: FertilityEstimate) -> None:
        self.snapshot = SimpleNamespace(fertility=estimate)


def _estimate(
    *,
    state: FertilityState = FertilityState.OUTSIDE_ESTIMATED_FERTILE_WINDOW,
    window: tuple[date, date] | None = (date(2026, 12, 8), date(2026, 12, 13)),
    band: tuple[date, date] | None = (date(2026, 12, 6), date(2026, 12, 15)),
    previous: tuple[date, date] | None = (date(2026, 11, 8), date(2026, 11, 17)),
    next_edge: tuple[date, date] | None = (date(2026, 12, 6), date(2026, 12, 15)),
    days_ago: int | None = 3,
) -> FertilityEstimate:
    """Build a controlled estimate for attribute serialization assertions."""
    return FertilityEstimate(
        state=state,
        fertile_window=window,
        margin_band=band,
        margin_days=2,
        confidence=0.33,
        confidence_band=ConfidenceBand.LOW,
        usable_cycle_count=2,
        previous_margin_band=previous,
        next_margin_band=next_edge,
        previous_band_days_ago=days_ago,
    )


def _sensor(estimate: FertilityEstimate) -> Any:
    """Return a fertility sensor reading a controlled coordinator snapshot."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    return FertilityEstimateSensor(
        _StubCoordinator(estimate),  # type: ignore[arg-type]
        entry,
    )


# --- constants and attribute shape ---------------------------------------------


def test_new_attribute_constants_have_stable_names() -> None:
    assert ATTR_PREVIOUS_MARGIN_BAND == "previous_margin_band"
    assert ATTR_NEXT_MARGIN_BAND == "next_margin_band"
    assert ATTR_PREVIOUS_BAND_DAYS_AGO == "previous_band_days_ago"


def test_sensor_exposes_exactly_nine_attributes() -> None:
    attributes = _sensor(_estimate()).extra_state_attributes

    assert set(attributes) == ALL_ATTRIBUTES


# --- serialization -------------------------------------------------------------


def test_previous_band_days_ago_is_serialized_as_an_integer() -> None:
    attributes = _sensor(_estimate()).extra_state_attributes

    assert attributes[ATTR_PREVIOUS_BAND_DAYS_AGO] == 3
    assert isinstance(attributes[ATTR_PREVIOUS_BAND_DAYS_AGO], int)


def test_both_edges_are_serialized_as_iso_pairs() -> None:
    attributes = _sensor(_estimate()).extra_state_attributes

    assert attributes[ATTR_PREVIOUS_MARGIN_BAND] == ("2026-11-08", "2026-11-17")
    assert attributes[ATTR_NEXT_MARGIN_BAND] == ("2026-12-06", "2026-12-15")


def test_only_next_edge_is_serialized_when_previous_is_absent() -> None:
    estimate = _estimate(
        window=(date(2026, 11, 10), date(2026, 11, 15)),
        band=(date(2026, 11, 8), date(2026, 11, 17)),
        previous=None,
        next_edge=(date(2026, 11, 8), date(2026, 11, 17)),
        days_ago=None,
    )

    attributes = _sensor(estimate).extra_state_attributes

    assert attributes[ATTR_PREVIOUS_MARGIN_BAND] is None
    assert attributes[ATTR_NEXT_MARGIN_BAND] == ("2026-11-08", "2026-11-17")
    assert attributes[ATTR_PREVIOUS_BAND_DAYS_AGO] is None
    assert attributes[ATTR_MARGIN_BAND] == attributes[ATTR_NEXT_MARGIN_BAND]


@pytest.mark.parametrize(
    "state",
    [FertilityState.WITHIN_ESTIMATED_FERTILE_WINDOW, FertilityState.UNKNOWN],
)
def test_absent_edges_are_serialized_as_none(state: FertilityState) -> None:
    estimate = _estimate(state=state, previous=None, next_edge=None, days_ago=None)

    attributes = _sensor(estimate).extra_state_attributes

    assert attributes[ATTR_PREVIOUS_MARGIN_BAND] is None
    assert attributes[ATTR_NEXT_MARGIN_BAND] is None
    assert attributes[ATTR_PREVIOUS_BAND_DAYS_AGO] is None


def test_eight_existing_attributes_keep_their_values() -> None:
    attributes = _sensor(_estimate()).extra_state_attributes

    assert attributes[ATTR_ESTIMATED_FERTILE_WINDOW] == ("2026-12-08", "2026-12-13")
    assert attributes[ATTR_MARGIN_BAND] == ("2026-12-06", "2026-12-15")
    assert attributes[ATTR_MARGIN_DAYS] == 2
    assert attributes[ATTR_PREDICTION_CONFIDENCE] == 0.33
    assert attributes[ATTR_CONFIDENCE_BAND] == "low"
    assert attributes[ATTR_USABLE_CYCLE_COUNT] == 2


# --- real wiring ---------------------------------------------------------------


async def test_entity_edges_follow_the_real_snapshot(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """The real sensor reads both new fields from the computed snapshot."""
    last_start = date(2026, 10, 24)
    for days_ago in (56, 28, 0):
        coordinator.add_period(period_row(last_start - timedelta(days=days_ago)))
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    estimate = coordinator.snapshot.fertility
    assert estimate.state is FertilityState.OUTSIDE_ESTIMATED_FERTILE_WINDOW
    assert estimate.previous_margin_band is not None
    assert estimate.next_margin_band is not None

    # The fertility entity is opt-in; inspect a directly built one instead.
    attributes = FertilityEstimateSensor(
        coordinator, config_entry
    ).extra_state_attributes
    assert attributes[ATTR_PREVIOUS_MARGIN_BAND] == tuple(
        day.isoformat() for day in estimate.previous_margin_band
    )
    assert attributes[ATTR_NEXT_MARGIN_BAND] == tuple(
        day.isoformat() for day in estimate.next_margin_band
    )
    assert (
        attributes[ATTR_PREVIOUS_BAND_DAYS_AGO]
        == (frozen_today - estimate.previous_margin_band[1]).days
    )


async def test_other_sensors_gain_no_gap_attributes(
    hass: HomeAssistant,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    last_start = date(2026, 11, 3)
    for days_ago in (56, 28, 0):
        coordinator.add_period(period_row(last_start - timedelta(days=days_ago)))
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    for entity_id in EXISTING_SENSOR_IDS:
        state = hass.states.get(entity_id)
        assert state is not None, entity_id
        assert NEW_ATTRIBUTES.isdisjoint(state.attributes), entity_id
