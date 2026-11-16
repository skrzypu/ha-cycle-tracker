"""The prediction pipeline, its windows and phase derivation (tasks 5.1-6.3)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, timedelta

import pytest
from domain.history import build_history
from domain.models import (
    ConfidenceBand,
    CyclePhase,
    Period,
    Prediction,
    WarningKind,
)
from domain.ports import PredictionConfig
from domain.prediction import cycle_day, phase_at, predict
from domain.statistics import statistics
from domain.strategies import DEFAULT_STRATEGY

CONFIG = PredictionConfig(period_length=5, cycle_length=28)
TODAY = date(2026, 11, 13)


def _predict(
    periods: list[Period],
    today: date = TODAY,
    strategy: str = DEFAULT_STRATEGY,
    config: PredictionConfig = CONFIG,
) -> Prediction | None:
    return predict(periods, config, strategy, today)


# --- a prediction needs two usable cycles (5.1) ------------------------------


def test_no_periods_yield_no_prediction() -> None:
    assert _predict([]) is None


def test_one_period_yields_no_prediction(
    make_period: Callable[..., Period],
) -> None:
    assert _predict([make_period(date(2026, 1, 1))]) is None


def test_one_usable_cycle_yields_no_prediction(
    make_periods: Callable[..., list[Period]],
) -> None:
    assert _predict(make_periods([28])) is None


def test_the_configured_cycle_length_is_never_a_fallback(
    make_period: Callable[..., Period],
) -> None:
    periods = [make_period(date(2026, 1, 1))]
    config = PredictionConfig(period_length=5, cycle_length=28)

    assert _predict(periods, config=config) is None


def test_a_single_usable_cycle_yields_no_prediction(
    make_periods: Callable[..., list[Period]],
) -> None:
    # 28 and 10 days: the 10-day cycle is excluded, leaving one usable cycle.
    assert _predict(make_periods([28, 10])) is None


def test_the_predicted_date_is_the_latest_start_plus_the_predicted_length(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([30, 30], first=date(2026, 9, 2))

    prediction = _predict(periods, strategy="arithmetic_mean")

    assert prediction is not None
    assert prediction.cycle_length_days == 30
    assert prediction.next_period == date(2026, 12, 1)


def test_the_predicted_length_comes_from_the_strategy_not_the_config(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28])
    config = PredictionConfig(period_length=5, cycle_length=99)

    prediction = _predict(periods, config=config)

    assert prediction is not None
    assert prediction.cycle_length_days == 28


def test_a_prediction_after_a_gap_needs_two_new_cycles(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1)),
        make_period(date(2026, 1, 29)),
        make_period(date(2026, 2, 26)),
        make_period(date(2026, 9, 1)),
        make_period(date(2026, 9, 29)),
    ]

    assert _predict(periods) is None

    periods.append(make_period(date(2026, 10, 27)))

    prediction = _predict(periods)

    assert prediction is not None
    assert prediction.next_period == date(2026, 11, 24)
    assert prediction.usable_cycle_count == 2


def test_the_window_never_reaches_across_a_gap(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1)),
        make_period(date(2026, 1, 29)),
        make_period(date(2026, 2, 26)),
        make_period(date(2026, 9, 1)),
    ]

    assert _predict(periods) is None


# --- strategies through the pipeline (4.3, 5.1) ------------------------------


def test_arithmetic_mean_strategy(
    make_periods: Callable[..., list[Period]],
) -> None:
    prediction = _predict(make_periods([26, 30, 31]), strategy="arithmetic_mean")

    assert prediction is not None
    assert prediction.cycle_length_days == 29


def test_weighted_moving_average_strategy(
    make_periods: Callable[..., list[Period]],
) -> None:
    prediction = _predict(make_periods([26, 30]), strategy="weighted_moving_average")

    assert prediction is not None
    assert prediction.cycle_length_days == 29


def test_median_strategy(
    make_periods: Callable[..., list[Period]],
) -> None:
    prediction = _predict(make_periods([26, 30, 31, 27]), strategy="median")

    assert prediction is not None
    assert prediction.cycle_length_days == 29


def test_the_default_strategy_is_the_weighted_moving_average(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([26, 30])

    assert _predict(periods) == _predict(periods, strategy="weighted_moving_average")


def test_an_unknown_strategy_falls_back_to_the_default(
    make_periods: Callable[..., list[Period]], caplog: pytest.LogCaptureFixture
) -> None:
    periods = make_periods([26, 30])

    with caplog.at_level(logging.WARNING):
        fallback = _predict(periods, strategy="prophet")

    assert fallback == _predict(periods, strategy=DEFAULT_STRATEGY)
    assert any(record.levelno is logging.WARNING for record in caplog.records)


# --- uncertainty window (5.2) -------------------------------------------------


def test_the_uncertainty_floor_is_two_days_for_a_stable_history(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))

    prediction = _predict(periods)

    assert prediction is not None
    assert prediction.uncertainty == (
        prediction.next_period - timedelta(days=2),
        prediction.next_period + timedelta(days=2),
    )


def test_a_variable_history_widens_the_uncertainty_window(
    make_periods: Callable[..., list[Period]],
) -> None:
    # 25, 32, 26, 33: population sigma is about 3.5, so the half-width is 4
    periods = make_periods([25, 32, 26, 33])

    prediction = _predict(periods)

    assert prediction is not None
    assert prediction.uncertainty == (
        prediction.next_period - timedelta(days=4),
        prediction.next_period + timedelta(days=4),
    )


# --- ovulation and fertile windows (5.3) --------------------------------------


def test_the_ovulation_window_sits_around_the_center(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))

    prediction = _predict(periods)

    assert prediction is not None
    assert prediction.next_period == date(2026, 12, 1)
    assert prediction.ovulation_center == date(2026, 11, 17)
    assert prediction.ovulation == (date(2026, 11, 15), date(2026, 11, 19))


def test_the_fertile_window_runs_five_days_before_ovulation(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))

    prediction = _predict(periods)

    assert prediction is not None
    assert prediction.fertile == (date(2026, 11, 12), date(2026, 11, 17))


def test_the_windows_are_clamped_to_the_current_cycle_start(
    make_periods: Callable[..., list[Period]],
) -> None:
    # 15-day cycles put the ovulation center one day after the cycle start.
    periods = make_periods([15, 15], first=date(2026, 1, 1))

    prediction = _predict(periods)

    assert prediction is not None
    latest_start = date(2026, 1, 31)
    assert prediction.ovulation_center == date(2026, 2, 1)
    assert prediction.ovulation[0] == latest_start
    assert prediction.fertile[0] == latest_start


def test_days_until_ovulation_is_measured_from_the_reference_date(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))

    prediction = _predict(periods, today=date(2026, 11, 13))

    assert prediction is not None
    assert prediction.days_until_ovulation == 4


def test_days_until_ovulation_is_zero_once_the_window_has_passed(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))

    prediction = _predict(periods, today=date(2026, 11, 20))

    assert prediction is not None
    assert prediction.days_until_ovulation == 0


# --- confidence (5.4) ---------------------------------------------------------


def test_two_stable_cycles_score_low_confidence(
    make_periods: Callable[..., list[Period]],
) -> None:
    prediction = _predict(make_periods([28, 28]))

    assert prediction is not None
    assert prediction.confidence == pytest.approx(1 / 3)
    assert prediction.confidence_band is ConfidenceBand.LOW


def test_four_variable_cycles_score_medium_confidence(
    make_periods: Callable[..., list[Period]],
) -> None:
    prediction = _predict(make_periods([25, 32, 26, 33]))

    assert prediction is not None
    assert prediction.confidence == pytest.approx(0.5854, abs=1e-4)
    assert prediction.confidence_band is ConfidenceBand.MEDIUM


def test_six_stable_cycles_score_high_confidence(
    make_periods: Callable[..., list[Period]],
) -> None:
    prediction = _predict(make_periods([26, 29, 29, 28, 28, 28]))

    assert prediction is not None
    assert prediction.confidence == pytest.approx(0.9643, abs=1e-4)
    assert prediction.confidence_band is ConfidenceBand.HIGH


def test_confidence_describes_the_data_not_the_strategy(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 30, 27])

    mean = _predict(periods, strategy="arithmetic_mean")
    median = _predict(periods, strategy="median")

    assert mean is not None
    assert median is not None
    assert mean.confidence == pytest.approx(median.confidence)


def test_confidence_matches_the_statistics_sensor(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))

    prediction = _predict(periods)
    result = statistics(periods, build_history(periods, CONFIG), CONFIG)

    assert prediction is not None
    assert prediction.confidence == pytest.approx(result.confidence)
    assert prediction.confidence_band is result.confidence_band


# --- late state and days until (5.5) -----------------------------------------


def test_days_until_a_future_period(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([30, 30], first=date(2026, 9, 2))

    prediction = _predict(periods, today=date(2026, 11, 28))

    assert prediction is not None
    assert prediction.next_period == date(2026, 12, 1)
    assert prediction.days_until_period == 3
    assert prediction.is_late is False
    assert prediction.days_late == 0


def test_the_period_due_today_is_not_late(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([30, 30], first=date(2026, 9, 2))

    prediction = _predict(periods, today=date(2026, 12, 1))

    assert prediction is not None
    assert prediction.days_until_period == 0
    assert prediction.is_late is False
    assert prediction.days_late == 0


def test_a_late_period_is_reported_without_moving_the_date(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([30, 30], first=date(2026, 9, 2))

    prediction = _predict(periods, today=date(2026, 12, 6))

    assert prediction is not None
    assert prediction.next_period == date(2026, 12, 1)
    assert prediction.days_until_period == 0
    assert prediction.is_late is True
    assert prediction.days_late == 5


def test_due_today_and_four_days_late_are_distinguishable(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([30, 30], first=date(2026, 9, 2))

    prediction = _predict(periods, today=date(2026, 12, 5))

    assert prediction is not None
    assert prediction.days_until_period == 0
    assert prediction.is_late is True
    assert prediction.days_late == 4


def test_a_new_start_clears_the_late_state(
    make_periods: Callable[..., list[Period]],
    make_period: Callable[..., Period],
) -> None:
    periods = make_periods([30, 30], first=date(2026, 9, 2))
    periods.append(make_period(date(2026, 12, 4)))

    prediction = _predict(periods, today=date(2026, 12, 6))

    assert prediction is not None
    assert prediction.is_late is False
    assert prediction.days_late == 0
    assert prediction.days_until_period > 0


# --- warnings and usable count (3.5) ----------------------------------------


def test_warnings_are_carried_on_the_prediction(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 10, 29])

    prediction = _predict(periods)

    assert prediction is not None
    assert prediction.warnings == build_history(periods, CONFIG).warnings
    assert [warning.kind for warning in prediction.warnings] == [WarningKind.OUTLIER]
    assert prediction.usable_cycle_count == 2


def test_the_usable_count_is_the_window_size(
    make_periods: Callable[..., list[Period]],
) -> None:
    prediction = _predict(make_periods([27, 28, 29, 28, 30, 28, 31, 29]))

    assert prediction is not None
    assert prediction.usable_cycle_count == 6


# --- determinism and the reference date (cycle-prediction spec) --------------


def test_the_same_inputs_produce_the_same_prediction(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))
    today = date(2026, 11, 13)

    assert _predict(periods, today=today) == _predict(periods, today=today)


def test_only_reference_date_dependent_values_change_with_the_date(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([30, 30], first=date(2026, 9, 2))

    before = _predict(periods, today=date(2026, 11, 28))
    after = _predict(periods, today=date(2026, 12, 5))

    assert before is not None
    assert after is not None
    assert before.next_period == after.next_period
    assert before.cycle_length_days == after.cycle_length_days
    assert before.uncertainty == after.uncertainty
    assert before.ovulation == after.ovulation
    assert before.fertile == after.fertile
    assert before.confidence == after.confidence
    assert before.usable_cycle_count == after.usable_cycle_count
    assert before.days_until_period != after.days_until_period
    assert before.is_late is False
    assert after.is_late is True


# --- elapsed cycle day (cycle-tracking delta) --------------------------------


def test_cycle_day_is_unknown_without_a_period() -> None:
    assert cycle_day([], TODAY) is None


def test_cycle_day_is_one_on_the_start_date(
    make_period: Callable[..., Period],
) -> None:
    periods = [make_period(date(2026, 1, 1))]

    assert cycle_day(periods, date(2026, 1, 1)) == 1


def test_cycle_day_counts_forward_without_wrapping(
    make_period: Callable[..., Period],
) -> None:
    periods = [make_period(date(2026, 1, 1))]

    assert cycle_day(periods, date(2026, 1, 3)) == 3
    assert cycle_day(periods, date(2026, 2, 3)) == 34


def test_cycle_day_uses_the_latest_start(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1)),
        make_period(date(2026, 2, 1)),
    ]

    assert cycle_day(periods, date(2026, 2, 5)) == 5


def test_cycle_day_is_unknown_before_the_first_start(
    make_period: Callable[..., Period],
) -> None:
    periods = [make_period(date(2026, 1, 1))]

    assert cycle_day(periods, date(2025, 12, 31)) is None


# --- phase derivation (6.1-6.3) ---------------------------------------------


def test_the_default_cycle_phase_boundaries(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))
    prediction = _predict(periods)
    assert prediction is not None
    expected = (
        [CyclePhase.MENSTRUAL] * 5
        + [CyclePhase.FOLLICULAR] * 7
        + [CyclePhase.OVULATORY] * 5
        + [CyclePhase.LUTEAL] * 11
    )

    actual = [
        phase_at(periods, prediction, CONFIG, date(2026, 11, 3) + timedelta(days=day))
        for day in range(28)
    ]

    assert actual == expected


def test_a_completed_cycle_uses_its_actual_next_start(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28])
    prediction = _predict(periods)
    assert prediction is not None
    # The current prediction's centre is 2026-03-12; the closed January cycle's
    # centre is the actual next start minus 14 days, 2026-01-15.
    assert prediction.ovulation_center == date(2026, 3, 12)

    assert (
        phase_at(periods, prediction, CONFIG, date(2026, 1, 15)) is CyclePhase.OVULATORY
    )
    assert (
        phase_at(periods, prediction, CONFIG, date(2026, 1, 12))
        is CyclePhase.FOLLICULAR
    )
    assert phase_at(periods, prediction, CONFIG, date(2026, 1, 28)) is CyclePhase.LUTEAL


def test_no_prediction_means_no_phase(
    make_periods: Callable[..., list[Period]],
) -> None:
    assert phase_at(make_periods([28, 28]), None, CONFIG, TODAY) is None


def test_no_phase_before_the_first_recorded_start(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))
    prediction = _predict(periods)

    assert phase_at(periods, prediction, CONFIG, date(2026, 9, 7)) is None


def test_the_configured_period_length_wins_over_the_ovulation_window(
    make_periods: Callable[..., list[Period]],
) -> None:
    config = PredictionConfig(period_length=7, cycle_length=28)
    periods = make_periods([21, 21], first=date(2026, 1, 1))
    prediction = _predict(periods, config=config)
    assert prediction is not None
    assert prediction.next_period == date(2026, 3, 5)
    expected = (
        [CyclePhase.MENSTRUAL] * 7
        + [CyclePhase.OVULATORY] * 3
        + [CyclePhase.LUTEAL] * 11
    )

    actual = [
        phase_at(periods, prediction, config, date(2026, 2, 12) + timedelta(days=day))
        for day in range(21)
    ]

    assert actual == expected


def test_no_ovulatory_phase_when_the_period_swallows_the_window(
    make_periods: Callable[..., list[Period]],
) -> None:
    config = PredictionConfig(period_length=10, cycle_length=28)
    periods = make_periods([21, 21], first=date(2026, 1, 1))
    prediction = _predict(periods, config=config)
    assert prediction is not None

    phases = {
        phase_at(periods, prediction, config, date(2026, 2, 12) + timedelta(days=day))
        for day in range(21)
    }

    assert CyclePhase.OVULATORY not in phases
    assert CyclePhase.FOLLICULAR not in phases
    assert CyclePhase.MENSTRUAL in phases
    assert CyclePhase.LUTEAL in phases


def test_a_late_cycle_stays_luteal_until_a_new_start(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28], first=date(2026, 9, 8))
    prediction = _predict(periods, today=date(2026, 12, 6))
    assert prediction is not None
    assert prediction.is_late is True

    assert phase_at(periods, prediction, CONFIG, date(2026, 12, 6)) is CyclePhase.LUTEAL
