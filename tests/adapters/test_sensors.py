"""Tests for the Cycle Tracker sensors reading the prediction snapshot."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from statistics import fmean
from typing import Any

import pytest

from custom_components.cycle_tracker.const import (
    ATTR_AVERAGE_CYCLE_LENGTH,
    ATTR_AVERAGE_PERIOD_LENGTH,
    ATTR_CONFIDENCE_BAND,
    ATTR_DAYS_LATE,
    ATTR_DAYS_UNTIL_PERIOD,
    ATTR_FERTILE_WINDOW_END,
    ATTR_FERTILE_WINDOW_START,
    ATTR_IS_LATE,
    ATTR_LIFETIME_AVERAGE_CYCLE_LENGTH,
    ATTR_OVULATION_WINDOW_END,
    ATTR_OVULATION_WINDOW_START,
    ATTR_PREDICTED_CYCLE_LENGTH,
    ATTR_PREDICTION_CONFIDENCE,
    ATTR_STD_DEV_CYCLE,
    ATTR_TOTAL_CYCLES_TRACKED,
    ATTR_UNCERTAINTY_END,
    ATTR_UNCERTAINTY_START,
    ATTR_USABLE_CYCLE_COUNT,
    ATTR_WARNINGS,
)
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator

PREDICTION_ENTITIES = (
    "sensor.cycle_tracker_cycle_day",
    "sensor.cycle_tracker_cycle_phase",
    "sensor.cycle_tracker_next_period_date",
    "sensor.cycle_tracker_next_ovulation_date",
    "sensor.cycle_tracker_days_until_period",
    "sensor.cycle_tracker_days_until_ovulation",
)


def _three_regular_cycles(
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    last_start: date,
) -> None:
    """Seed three four-week cycles ending in ``last_start``."""
    for weeks_ago in (8, 4, 0):
        coordinator.add_period(period_row(last_start - timedelta(weeks=weeks_ago)))
    coordinator.async_update_listeners()


def _seed_cycles(
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    lengths: list[int],
    last_start: date,
) -> None:
    """Seed period rows whose start-to-start lengths are ``lengths``."""
    starts = [last_start]
    for length in reversed(lengths):
        starts.insert(0, starts[0] - timedelta(days=length))
    for start in starts:
        coordinator.add_period(period_row(start))
    coordinator.async_update_listeners()


async def test_prediction_entities_are_unknown_without_history(
    hass,
    coordinator: CycleTrackerCoordinator,
) -> None:
    """A fresh install reports unknown instead of zero values."""
    for entity_id in PREDICTION_ENTITIES:
        state = hass.states.get(entity_id)
        assert state is not None, entity_id
        assert state.state == "unknown", entity_id

    statistics = hass.states.get("sensor.cycle_tracker_statistics")
    assert statistics is not None
    assert statistics.state == "0"
    assert statistics.attributes[ATTR_PREDICTION_CONFIDENCE] is None
    assert statistics.attributes[ATTR_CONFIDENCE_BAND] is None


async def test_single_period_keeps_prediction_entities_unknown(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """One recorded period is not a usable cycle and produces no prediction."""
    coordinator.add_period(period_row(frozen_today))
    coordinator.async_update_listeners()

    assert hass.states.get("sensor.cycle_tracker_cycle_day").state == "1"
    assert hass.states.get("sensor.cycle_tracker_cycle_phase").state == "unknown"
    assert hass.states.get("sensor.cycle_tracker_next_period_date").state == "unknown"
    assert hass.states.get("sensor.cycle_tracker_days_until_period").state == "unknown"


async def test_cycle_start_date_reports_the_most_recent_start(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """The cycle start date sensor shows the most recent recorded start."""
    start = frozen_today - timedelta(days=10)
    coordinator.add_period(period_row(start))
    coordinator.async_update_listeners()

    state = hass.states.get("sensor.cycle_tracker_cycle_start_date")

    assert state is not None
    assert state.state == start.isoformat()


async def test_cycle_start_date_is_unknown_without_periods(
    hass,
    coordinator: CycleTrackerCoordinator,
) -> None:
    """With no recorded periods the cycle start date is unknown."""
    state = hass.states.get("sensor.cycle_tracker_cycle_start_date")

    assert state is not None
    assert state.state == "unknown"


async def test_cycle_day_counts_past_the_configured_length(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """Thirty-three elapsed days report cycle day 34 without wrapping."""
    coordinator.add_period(period_row(frozen_today - timedelta(days=33)))
    coordinator.async_update_listeners()

    state = hass.states.get("sensor.cycle_tracker_cycle_day")

    assert state is not None
    assert state.state == "34"


async def test_late_period_reports_zero_days_until_and_a_late_flag(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """A period four days overdue is distinguishable from one due today."""
    _three_regular_cycles(
        coordinator, period_row, last_start=frozen_today - timedelta(days=32)
    )

    days_until_period = hass.states.get("sensor.cycle_tracker_days_until_period")

    assert days_until_period is not None
    assert days_until_period.state == "0"
    assert days_until_period.attributes[ATTR_DAYS_UNTIL_PERIOD] == 0
    assert days_until_period.attributes[ATTR_IS_LATE] is True
    assert days_until_period.attributes[ATTR_DAYS_LATE] == 4

    next_period = hass.states.get("sensor.cycle_tracker_next_period_date")
    assert next_period is not None
    assert next_period.state == (frozen_today - timedelta(days=4)).isoformat()


async def test_prediction_windows_are_exposed(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """The uncertainty, ovulation and fertile windows come from the snapshot."""
    _three_regular_cycles(
        coordinator, period_row, last_start=frozen_today - timedelta(days=28)
    )

    next_period = hass.states.get("sensor.cycle_tracker_next_period_date")
    ovulation = hass.states.get("sensor.cycle_tracker_next_ovulation_date")

    assert next_period is not None
    assert ovulation is not None
    assert next_period.state == frozen_today.isoformat()
    assert next_period.attributes[ATTR_PREDICTED_CYCLE_LENGTH] == 28
    assert next_period.attributes[ATTR_USABLE_CYCLE_COUNT] == 2
    assert (
        next_period.attributes[ATTR_UNCERTAINTY_START]
        == (frozen_today - timedelta(days=2)).isoformat()
    )
    assert (
        next_period.attributes[ATTR_UNCERTAINTY_END]
        == (frozen_today + timedelta(days=2)).isoformat()
    )

    # The running cycle's ovulation has already passed, so the sensor reports
    # the next one: one cycle later, fourteen days before the following period.
    ovulation_center = frozen_today + timedelta(days=14)
    assert ovulation.state == ovulation_center.isoformat()
    assert (
        ovulation.attributes[ATTR_OVULATION_WINDOW_START]
        == (ovulation_center - timedelta(days=2)).isoformat()
    )
    assert (
        ovulation.attributes[ATTR_OVULATION_WINDOW_END]
        == (ovulation_center + timedelta(days=2)).isoformat()
    )
    assert (
        ovulation.attributes[ATTR_FERTILE_WINDOW_START]
        == (ovulation_center - timedelta(days=5)).isoformat()
    )
    assert ovulation.attributes[ATTR_FERTILE_WINDOW_END] == ovulation_center.isoformat()

    days_until_period = hass.states.get("sensor.cycle_tracker_days_until_period")
    assert days_until_period is not None
    assert days_until_period.state == "0"
    assert days_until_period.attributes[ATTR_IS_LATE] is False
    assert days_until_period.attributes[ATTR_DAYS_LATE] == 0


async def test_statistics_use_the_windowed_history(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """Statistics report the usable window plus confidence and warnings."""
    _three_regular_cycles(
        coordinator, period_row, last_start=frozen_today - timedelta(days=28)
    )

    state = hass.states.get("sensor.cycle_tracker_statistics")

    assert state is not None
    assert state.state == "3"
    assert state.attributes[ATTR_TOTAL_CYCLES_TRACKED] == 3
    assert state.attributes[ATTR_AVERAGE_CYCLE_LENGTH] == pytest.approx(28.0)
    assert state.attributes[ATTR_AVERAGE_PERIOD_LENGTH] == pytest.approx(5.0)
    assert state.attributes[ATTR_STD_DEV_CYCLE] == pytest.approx(0.0)
    assert state.attributes[ATTR_PREDICTION_CONFIDENCE] == pytest.approx(1 / 3)
    assert state.attributes[ATTR_CONFIDENCE_BAND] == "low"
    assert state.attributes[ATTR_WARNINGS] == []


async def test_statistics_expose_the_lifetime_average(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """The lifetime row covers every in-range cycle, the windowed row does not."""
    _seed_cycles(
        coordinator,
        period_row,
        [28, 10, 30, 31, 32, 33, 34, 35],
        frozen_today,
    )

    state = hass.states.get("sensor.cycle_tracker_statistics")

    assert state is not None
    assert state.attributes[ATTR_LIFETIME_AVERAGE_CYCLE_LENGTH] == pytest.approx(
        fmean([28, 30, 31, 32, 33, 34, 35])
    )
    assert state.attributes[ATTR_AVERAGE_CYCLE_LENGTH] == pytest.approx(
        fmean([30, 31, 32, 33, 34, 35])
    )


async def test_statistics_lifetime_average_is_none_without_in_range_cycles(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """Only out-of-range cycles leave the lifetime attribute present but unknown."""
    _seed_cycles(coordinator, period_row, [10, 12], frozen_today)

    state = hass.states.get("sensor.cycle_tracker_statistics")

    assert state is not None
    assert ATTR_LIFETIME_AVERAGE_CYCLE_LENGTH in state.attributes
    assert state.attributes[ATTR_LIFETIME_AVERAGE_CYCLE_LENGTH] is None


async def test_statistics_report_excluded_cycles_as_warnings(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, Any]],
    frozen_today: date,
) -> None:
    """An outlier leaves the prediction window and is named in the warnings."""
    coordinator.add_period(period_row(frozen_today - timedelta(days=94)))
    coordinator.add_period(period_row(frozen_today - timedelta(days=66)))
    coordinator.add_period(period_row(frozen_today - timedelta(days=56)))
    coordinator.add_period(period_row(frozen_today - timedelta(days=28)))
    coordinator.async_update_listeners()

    state = hass.states.get("sensor.cycle_tracker_statistics")

    assert state is not None
    warnings = state.attributes[ATTR_WARNINGS]
    assert [warning["kind"] for warning in warnings] == ["outlier"]
    assert isinstance(warnings[0]["period_id"], str)
