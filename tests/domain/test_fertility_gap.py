"""Both edges of the estimated fertility gap (change fertility-gap-both-bands).

These tests hold the domain half of the contract: in the ``outside`` state the
estimate carries the band the reference date just left and the band it is
approaching, computed purely from the prediction the snapshot already supplies.
The entity/attribute surface is covered separately in ``tests/adapters``.
"""

from __future__ import annotations

import dataclasses
from datetime import date, timedelta
from statistics import pstdev

import pytest
from domain.fertility import FertilityEstimate, FertilityState, fertility_estimate
from domain.models import ConfidenceBand, CycleWindows, Prediction
from domain.statistics import CycleStatistics

CENTER = date(2026, 11, 15)
NEXT_CENTER = date(2026, 12, 13)  # CENTER + 28 days
CURRENT_BAND = (date(2026, 11, 8), date(2026, 11, 17))
NEXT_BAND = (date(2026, 12, 6), date(2026, 12, 15))


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


def _windows(center: date) -> CycleWindows:
    """Build the unclamped windows of one 28-day cycle around ``center``."""
    return CycleWindows(
        period_start=center - timedelta(days=14),
        period_end=center - timedelta(days=10),
        next_period=center + timedelta(days=14),
        ovulation_center=center,
        ovulation=(center - timedelta(days=2), center + timedelta(days=2)),
        fertile=(center - timedelta(days=5), center),
    )


def _prediction(
    *,
    center: date = CENTER,
    next_is_current: bool = False,
    usable: int = 2,
) -> Prediction:
    """Build a prediction whose next ovulation is the following cycle by default.

    With ``next_is_current`` the next ovulation points at the running cycle, the
    situation the reference date is before any band and only one edge exists.
    """
    current = _windows(center)
    next_center = center if next_is_current else NEXT_CENTER
    return Prediction(
        next_period=current.next_period,
        cycle_length_days=28,
        uncertainty=(center + timedelta(days=12), center + timedelta(days=16)),
        ovulation=current.ovulation,
        ovulation_center=current.ovulation_center,
        fertile=current.fertile,
        next_ovulation=_windows(next_center),
        confidence=0.33,
        confidence_band=ConfidenceBand.LOW,
        is_late=False,
        days_late=0,
        days_until_period=0,
        days_until_ovulation=0,
        warnings=(),
        usable_cycle_count=usable,
    )


def _estimate() -> FertilityEstimate:
    """Return a directly constructed estimate used for model-shape assertions."""
    return FertilityEstimate(
        state=FertilityState.UNKNOWN,
        fertile_window=None,
        margin_band=None,
        margin_days=0,
        confidence=0.33,
        confidence_band=ConfidenceBand.LOW,
        usable_cycle_count=0,
    )


# --- frozen model --------------------------------------------------------------


def test_gap_fields_exist_on_the_frozen_model() -> None:
    names = {field.name for field in dataclasses.fields(FertilityEstimate)}

    assert "previous_margin_band" in names
    assert "next_margin_band" in names
    assert "previous_band_days_ago" in names


def test_gap_fields_default_to_none_when_constructed_directly() -> None:
    estimate = _estimate()

    assert estimate.previous_margin_band is None
    assert estimate.next_margin_band is None
    assert estimate.previous_band_days_ago is None


@pytest.mark.parametrize(
    "field_name",
    ["previous_margin_band", "next_margin_band", "previous_band_days_ago"],
)
def test_gap_fields_cannot_be_mutated(field_name: str) -> None:
    estimate = _estimate()

    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(estimate, field_name, (date(2026, 11, 8), date(2026, 11, 17)))


# --- outside: both edges -------------------------------------------------------


def test_both_edges_are_reported_between_the_bands() -> None:
    estimate = fertility_estimate(_prediction(), _statistics(), date(2026, 11, 20))

    assert estimate.state is FertilityState.OUTSIDE_ESTIMATED_FERTILE_WINDOW
    assert estimate.previous_margin_band == CURRENT_BAND
    assert estimate.next_margin_band == NEXT_BAND
    assert estimate.previous_band_days_ago == 3


@pytest.mark.parametrize(
    ("today", "days_ago"),
    [
        (date(2026, 11, 20), 3),
        (date(2026, 11, 21), 4),
        (date(2026, 11, 18), 1),
    ],
)
def test_days_ago_is_derived_from_the_reference_date(
    today: date, days_ago: int
) -> None:
    estimate = fertility_estimate(_prediction(), _statistics(), today)

    assert estimate.previous_margin_band == CURRENT_BAND
    assert estimate.previous_band_days_ago == days_ago


def test_only_the_prediction_next_ovulation_supplies_the_further_edge() -> None:
    estimate = fertility_estimate(_prediction(), _statistics(), date(2026, 11, 20))

    assert estimate.next_margin_band == (
        NEXT_CENTER - timedelta(days=7),
        NEXT_CENTER + timedelta(days=2),
    )
    # The archived attribute keeps carrying the next band (design decision 3).
    assert estimate.margin_band == estimate.next_margin_band


def test_margin_is_applied_to_both_edges() -> None:
    sigma = pstdev([25, 32, 26, 33])
    estimate = fertility_estimate(
        _prediction(usable=4),
        _statistics(sigma=sigma, usable=4),
        date(2026, 11, 20),
    )

    assert estimate.margin_days == 4
    assert estimate.previous_margin_band == (date(2026, 11, 6), date(2026, 11, 19))
    assert estimate.next_margin_band == (date(2026, 12, 4), date(2026, 12, 17))
    # The count follows the widened edge, not the original six-day window.
    assert estimate.previous_band_days_ago == 1


# --- outside: one edge ---------------------------------------------------------


def test_running_cycle_as_next_ovulation_has_no_previous_edge() -> None:
    estimate = fertility_estimate(
        _prediction(next_is_current=True), _statistics(), date(2026, 11, 1)
    )

    assert estimate.state is FertilityState.OUTSIDE_ESTIMATED_FERTILE_WINDOW
    assert estimate.previous_margin_band is None
    assert estimate.next_margin_band == CURRENT_BAND
    assert estimate.previous_band_days_ago is None


def test_absent_previous_edge_is_never_copied_from_the_next_one() -> None:
    estimate = fertility_estimate(
        _prediction(next_is_current=True), _statistics(), date(2026, 11, 1)
    )

    assert estimate.previous_margin_band is None
    assert estimate.next_margin_band is not None
    assert estimate.previous_margin_band != estimate.next_margin_band
    assert estimate.previous_band_days_ago is None


# --- within and unknown stay unchanged -----------------------------------------


@pytest.mark.parametrize(
    ("today", "window", "band"),
    [
        (date(2026, 11, 9), (date(2026, 11, 10), date(2026, 11, 15)), CURRENT_BAND),
        (date(2026, 12, 10), (date(2026, 12, 8), date(2026, 12, 13)), NEXT_BAND),
    ],
)
def test_within_either_band_reports_no_edges(
    today: date, window: tuple[date, date], band: tuple[date, date]
) -> None:
    estimate = fertility_estimate(_prediction(), _statistics(), today)

    assert estimate.state is FertilityState.WITHIN_ESTIMATED_FERTILE_WINDOW
    assert estimate.previous_margin_band is None
    assert estimate.next_margin_band is None
    assert estimate.previous_band_days_ago is None
    assert estimate.fertile_window == window
    assert estimate.margin_band == band
    assert estimate.margin_days == 2
    assert estimate.confidence == 0.33
    assert estimate.confidence_band is ConfidenceBand.LOW
    assert estimate.usable_cycle_count == 2


@pytest.mark.parametrize("usable", [0, 1])
def test_unknown_estimate_reports_no_edges(usable: int) -> None:
    prediction = None if usable == 0 else _prediction(usable=1)

    estimate = fertility_estimate(
        prediction, _statistics(usable=usable), date(2026, 11, 9)
    )

    assert estimate.state is FertilityState.UNKNOWN
    assert estimate.fertile_window is None
    assert estimate.margin_band is None
    assert estimate.previous_margin_band is None
    assert estimate.next_margin_band is None
    assert estimate.previous_band_days_ago is None
    assert estimate.usable_cycle_count == usable


# --- determinism ---------------------------------------------------------------


def test_identical_inputs_produce_identical_edges() -> None:
    prediction = _prediction()
    statistics = _statistics()
    first = fertility_estimate(prediction, statistics, date(2026, 11, 20))
    second = fertility_estimate(prediction, statistics, date(2026, 11, 20))

    assert first == second
    assert (first.previous_margin_band, first.next_margin_band) == (
        second.previous_margin_band,
        second.next_margin_band,
    )
    assert first.previous_band_days_ago == second.previous_band_days_ago == 3


def test_reference_date_changes_availability_but_not_band_geometry() -> None:
    prediction = _prediction()
    statistics = _statistics()
    within = fertility_estimate(prediction, statistics, date(2026, 11, 9))
    outside = fertility_estimate(prediction, statistics, date(2026, 11, 20))

    assert within.previous_margin_band is None
    assert within.next_margin_band is None
    assert within.previous_band_days_ago is None
    assert outside.previous_margin_band == within.margin_band == CURRENT_BAND
    assert outside.next_margin_band == NEXT_BAND
    assert outside.previous_band_days_ago == 3
    assert outside.margin_days == within.margin_days == 2
