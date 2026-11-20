"""Fertility estimate: uncertainty band, classification and snapshot wiring.

The fertility estimate is a pure presentation of the existing prediction's
fertile window. These tests hold the add-fertility-estimate contract at the
domain seam: the stable tokens, the frozen value object, the margin derived
from population sigma, the two-cycle minimum and determinism.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from datetime import date, timedelta
from statistics import pstdev

import pytest
from domain.fertility import (
    MIN_FERTILITY_MARGIN_DAYS,
    FertilityEstimate,
    FertilityState,
    fertility_estimate,
)
from domain.models import ConfidenceBand, Period, Prediction
from domain.ports import PredictionConfig
from domain.prediction import build_snapshot
from domain.statistics import CycleStatistics
from domain.strategies import DEFAULT_STRATEGY
from domain.windows import CycleWindows

CENTER = date(2026, 11, 15)
NEXT_CENTER = CENTER + timedelta(days=28)
CONFIG = PredictionConfig(period_length=5, cycle_length=28)
TODAY = date(2026, 11, 13)


def _statistics(*, sigma: float = 0.0, usable: int = 2) -> CycleStatistics:
    """Build statistics with a controlled sigma and usable-cycle count."""
    return CycleStatistics(
        average_cycle_length=28.0,
        average_period_length=5.0,
        cycle_length_std_dev=sigma,
        period_length_std_dev=0.0,
        total_cycles_tracked=usable + 1,
        shortest_cycle=28,
        longest_cycle=28,
        confidence=0.33,
        confidence_band=ConfidenceBand.LOW,
    )


def _prediction(
    *,
    center: date = CENTER,
    usable: int = 2,
    period_start: date | None = None,
) -> Prediction:
    """Build a prediction around a chosen ovulation centre.

    ``period_start`` can be placed after the unclamped fertile start so a test
    can prove the margin band is not clamped to the cycle start.
    """
    next_center = center + timedelta(days=28)
    start = period_start if period_start is not None else center - timedelta(days=14)
    return Prediction(
        next_period=center + timedelta(days=14),
        cycle_length_days=28,
        uncertainty=(center + timedelta(days=12), center + timedelta(days=16)),
        ovulation=(center - timedelta(days=2), center + timedelta(days=2)),
        ovulation_center=center,
        fertile=(max(center - timedelta(days=5), start), center),
        next_ovulation=CycleWindows(
            period_start=next_center - timedelta(days=14),
            period_end=next_center - timedelta(days=10),
            next_period=next_center + timedelta(days=14),
            ovulation_center=next_center,
            ovulation=(
                next_center - timedelta(days=2),
                next_center + timedelta(days=2),
            ),
            fertile=(next_center - timedelta(days=5), next_center),
        ),
        confidence=0.33,
        confidence_band=ConfidenceBand.LOW,
        is_late=False,
        days_late=0,
        days_until_period=0,
        days_until_ovulation=0,
        warnings=(),
        usable_cycle_count=usable,
    )


# --- model -------------------------------------------------------------------


def test_fertility_state_has_exactly_three_stable_tokens() -> None:
    assert len(list(FertilityState)) == 3
    assert {state.value for state in FertilityState} == {
        "outside_estimated_fertile_window",
        "within_estimated_fertile_window",
        "unknown",
    }
    assert FertilityState("unknown") is FertilityState.UNKNOWN


def test_fertility_estimate_is_frozen() -> None:
    estimate = FertilityEstimate(
        state=FertilityState.UNKNOWN,
        fertile_window=None,
        margin_band=None,
        margin_days=0,
        confidence=0.33,
        confidence_band=ConfidenceBand.LOW,
        usable_cycle_count=0,
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        estimate.margin_days = 4  # type: ignore[misc]


# --- margin from population sigma --------------------------------------------


def test_margin_documented_floor_is_two_days() -> None:
    assert MIN_FERTILITY_MARGIN_DAYS == 2


def test_stable_history_uses_the_two_day_floor() -> None:
    estimate = fertility_estimate(
        _prediction(), _statistics(sigma=0.0), date(2026, 11, 9)
    )

    assert estimate.margin_days == 2


@pytest.mark.parametrize(
    ("sigma", "margin"),
    [(0.0, 2), (1.25, 2), (2.0, 2), (2.25, 3), (3.5355, 4)],
)
def test_margin_is_max_two_and_ceil_sigma(sigma: float, margin: int) -> None:
    estimate = fertility_estimate(_prediction(), _statistics(sigma=sigma), CENTER)

    assert estimate.margin_days == margin


def test_variable_history_widens_the_margin_to_four_days() -> None:
    sigma = pstdev([25, 32, 26, 33])

    assert sigma == pytest.approx(3.5355, abs=1e-4)
    estimate = fertility_estimate(
        _prediction(usable=4), _statistics(sigma=sigma, usable=4), date(2026, 11, 9)
    )

    assert estimate.margin_days == 4


# --- band geometry ------------------------------------------------------------


def test_band_around_a_stable_cycle_keeps_the_base_window() -> None:
    prediction = _prediction()

    estimate = fertility_estimate(prediction, _statistics(), date(2026, 11, 9))

    assert estimate.fertile_window == (date(2026, 11, 10), date(2026, 11, 15))
    assert estimate.margin_band == (date(2026, 11, 8), date(2026, 11, 17))


def test_band_grows_with_irregular_cycles() -> None:
    sigma = pstdev([25, 32, 26, 33])
    stable = fertility_estimate(
        _prediction(usable=4), _statistics(sigma=0.0, usable=4), date(2026, 11, 9)
    )
    irregular = fertility_estimate(
        _prediction(usable=4), _statistics(sigma=sigma, usable=4), date(2026, 11, 9)
    )

    assert irregular.fertile_window == stable.fertile_window
    assert irregular.margin_band == (date(2026, 11, 6), date(2026, 11, 19))
    assert irregular.margin_band[0] < stable.margin_band[0]
    assert irregular.margin_band[1] > stable.margin_band[1]


def test_bands_are_not_clamped_to_the_cycle_start() -> None:
    # The base window is clamped to the cycle start; the margin band is not.
    cycle_start = date(2026, 11, 12)
    prediction = _prediction(period_start=cycle_start)

    estimate = fertility_estimate(prediction, _statistics(), date(2026, 11, 13))

    assert estimate.fertile_window == (cycle_start, CENTER)
    assert estimate.margin_band == (date(2026, 11, 10), date(2026, 11, 17))
    assert estimate.margin_band[0] < cycle_start


# --- classification -----------------------------------------------------------


def test_date_inside_the_extended_band_is_within() -> None:
    estimate = fertility_estimate(_prediction(), _statistics(), date(2026, 11, 9))

    assert estimate.state is FertilityState.WITHIN_ESTIMATED_FERTILE_WINDOW
    assert estimate.margin_band is not None
    assert estimate.margin_band[0] <= date(2026, 11, 9) <= estimate.margin_band[1]


def test_date_between_bands_is_outside() -> None:
    estimate = fertility_estimate(_prediction(), _statistics(), date(2026, 11, 20))

    assert estimate.state is FertilityState.OUTSIDE_ESTIMATED_FERTILE_WINDOW
    assert estimate.margin_band == (
        NEXT_CENTER - timedelta(days=7),
        NEXT_CENTER + timedelta(days=2),
    )


def test_boundary_dates_are_inclusive() -> None:
    prediction = _prediction()
    statistics = _statistics()

    for boundary in (date(2026, 11, 8), date(2026, 11, 17)):
        estimate = fertility_estimate(prediction, statistics, boundary)
        assert estimate.state is FertilityState.WITHIN_ESTIMATED_FERTILE_WINDOW


def test_no_prediction_is_unknown_without_a_window_or_a_fallback() -> None:
    statistics = _statistics()  # average cycle length 28, sigma 0

    estimate = fertility_estimate(None, statistics, date(2026, 11, 9))

    assert estimate.state is FertilityState.UNKNOWN
    assert estimate.fertile_window is None
    assert estimate.margin_band is None
    assert estimate.usable_cycle_count == 0


def test_one_usable_cycle_is_unknown_without_a_window() -> None:
    estimate = fertility_estimate(
        _prediction(usable=1), _statistics(usable=1), date(2026, 11, 9)
    )

    assert estimate.state is FertilityState.UNKNOWN
    assert estimate.fertile_window is None
    assert estimate.margin_band is None
    assert estimate.usable_cycle_count == 1


def test_estimate_carries_confidence_and_cycle_count() -> None:
    estimate = fertility_estimate(
        _prediction(usable=4), _statistics(sigma=3.5, usable=4), date(2026, 11, 9)
    )

    assert estimate.confidence == 0.33
    assert estimate.confidence_band is ConfidenceBand.LOW
    assert estimate.usable_cycle_count == 4


# --- determinism --------------------------------------------------------------


def test_identical_inputs_produce_identical_estimates() -> None:
    prediction = _prediction()
    statistics = _statistics()

    first = fertility_estimate(prediction, statistics, date(2026, 11, 9))
    second = fertility_estimate(prediction, statistics, date(2026, 11, 9))

    assert first == second


def test_reference_date_changes_state_but_not_the_band_for_a_center() -> None:
    prediction = _prediction()
    statistics = _statistics()

    outside = fertility_estimate(prediction, statistics, date(2026, 11, 20))
    within = fertility_estimate(prediction, statistics, NEXT_CENTER - timedelta(days=2))

    assert outside.state is FertilityState.OUTSIDE_ESTIMATED_FERTILE_WINDOW
    assert within.state is FertilityState.WITHIN_ESTIMATED_FERTILE_WINDOW
    assert outside.margin_band == within.margin_band
    assert outside.fertile_window == within.fertile_window


# --- snapshot always carries the estimate ------------------------------------


def test_snapshot_fills_fertility_for_two_usable_cycles(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))

    snapshot = build_snapshot(periods, CONFIG, DEFAULT_STRATEGY, TODAY)

    assert snapshot.prediction is not None
    assert snapshot.fertility.margin_days == 2
    assert snapshot.fertility.state is FertilityState.WITHIN_ESTIMATED_FERTILE_WINDOW
    assert snapshot.fertility.fertile_window == (date(2026, 11, 12), date(2026, 11, 17))
    assert snapshot.fertility.margin_band == (date(2026, 11, 10), date(2026, 11, 19))
    assert snapshot.fertility.usable_cycle_count == 2


@pytest.mark.parametrize(
    "lengths",
    [[], [28]],
)
def test_snapshot_fertility_is_unknown_below_two_cycles(
    make_periods: Callable[..., list[Period]],
    lengths: list[int],
) -> None:
    periods = make_periods(lengths, first=date(2026, 9, 8))

    snapshot = build_snapshot(periods, CONFIG, DEFAULT_STRATEGY, TODAY)

    assert snapshot.prediction is None
    assert snapshot.fertility.state is FertilityState.UNKNOWN
    assert snapshot.fertility.fertile_window is None
    assert snapshot.fertility.margin_band is None
