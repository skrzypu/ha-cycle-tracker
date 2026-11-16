"""Statistics derived from the shared usable window (tasks 8.1-8.2)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from statistics import fmean, pstdev

import pytest
from domain.history import build_history
from domain.models import ConfidenceBand, Period
from domain.ports import PredictionConfig
from domain.statistics import CycleStatistics, statistics

CONFIG = PredictionConfig(period_length=5, cycle_length=28)


def _measure(
    periods: list[Period], config: PredictionConfig = CONFIG
) -> CycleStatistics:
    return statistics(periods, build_history(periods, config), config)


def test_a_single_period_reports_the_configured_lengths(
    make_period: Callable[..., Period],
) -> None:
    periods = [make_period(date(2026, 1, 1), end=date(2026, 1, 5))]

    result = _measure(periods)

    assert result.average_cycle_length == 28.0
    assert result.average_period_length == 5.0
    assert result.cycle_length_std_dev == 0.0
    assert result.period_length_std_dev == 0.0
    assert result.shortest_cycle == 28
    assert result.longest_cycle == 28
    assert result.total_cycles_tracked == 1
    assert result.confidence is None
    assert result.confidence_band is None


def test_no_periods_report_the_configured_lengths_and_a_zero_count() -> None:
    result = _measure([])

    assert result.average_cycle_length == 28.0
    assert result.average_period_length == 5.0
    assert result.total_cycles_tracked == 0
    assert result.confidence is None


def test_one_usable_cycle_still_uses_the_configured_fallback(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28])

    result = _measure(periods)

    assert result.average_cycle_length == 28.0
    assert result.cycle_length_std_dev == 0.0
    assert result.total_cycles_tracked == 2
    assert result.confidence is None


def test_multiple_cycles_are_averaged_from_the_prediction_window(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 29, 30])

    result = _measure(periods)

    assert result.average_cycle_length == pytest.approx(fmean([28, 29, 30]))
    assert result.cycle_length_std_dev == pytest.approx(pstdev([28, 29, 30]))
    assert result.shortest_cycle == 28
    assert result.longest_cycle == 30


def test_cycle_statistics_ignore_cycles_outside_the_window(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([20, 21, 22, 23, 24, 25, 26, 27])

    result = _measure(periods)

    assert result.average_cycle_length == pytest.approx(24.5)
    assert result.cycle_length_std_dev == pytest.approx(
        pstdev([22, 23, 24, 25, 26, 27])
    )
    assert result.shortest_cycle == 22
    assert result.longest_cycle == 27
    assert result.total_cycles_tracked == 9


def test_cycle_statistics_restart_after_a_long_gap(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1)),
        make_period(date(2026, 1, 29)),
        make_period(date(2026, 2, 26)),
        make_period(date(2026, 9, 1)),
        make_period(date(2026, 9, 29)),
        make_period(date(2026, 10, 28)),
    ]

    result = _measure(periods)

    assert result.average_cycle_length == pytest.approx(fmean([28, 29]))
    assert result.total_cycles_tracked == 6


def test_period_lengths_use_completed_periods_only(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1), end=date(2026, 1, 5)),
        make_period(date(2026, 1, 29), end=date(2026, 2, 1)),
        make_period(date(2026, 2, 26)),
    ]

    result = _measure(periods)

    assert result.average_period_length == pytest.approx(4.5)
    assert result.period_length_std_dev == pytest.approx(0.5)
    assert result.total_cycles_tracked == 3


def test_a_period_that_ends_before_it_starts_is_ignored(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1), end=date(2026, 1, 5)),
        make_period(date(2026, 1, 29), end=date(2026, 1, 20)),
        make_period(date(2026, 2, 26), end=date(2026, 3, 2)),
    ]

    result = _measure(periods)

    assert result.average_period_length == pytest.approx(5.0)
    assert result.total_cycles_tracked == 3


def test_total_cycles_tracked_counts_every_recorded_period(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1), end=date(2026, 1, 5)),
        make_period(date(2026, 1, 29), end=date(2026, 2, 2)),
        make_period(date(2026, 2, 26), end=date(2026, 3, 2)),
        make_period(date(2026, 3, 26)),
    ]

    result = _measure(periods)

    assert result.total_cycles_tracked == 4


def test_two_stable_cycles_score_low_confidence(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28])

    result = _measure(periods)

    assert result.confidence == pytest.approx(1 / 3)
    assert result.confidence_band is ConfidenceBand.LOW


def test_four_variable_cycles_score_medium_confidence(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([25, 32, 26, 33])

    result = _measure(periods)

    assert result.confidence == pytest.approx(0.5854, abs=1e-4)
    assert result.confidence_band is ConfidenceBand.MEDIUM


def test_six_stable_cycles_score_high_confidence(
    make_periods: Callable[..., list[Period]],
) -> None:
    # mean 28, population standard deviation exactly 1
    periods = make_periods([26, 29, 29, 28, 28, 28])

    result = _measure(periods)

    assert result.cycle_length_std_dev == pytest.approx(1.0)
    assert result.confidence == pytest.approx(0.9643, abs=1e-4)
    assert result.confidence_band is ConfidenceBand.HIGH
