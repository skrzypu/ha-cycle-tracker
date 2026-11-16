"""Deriving cycles, the usable window and data warnings (tasks 3.1-3.5)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from domain.history import History, build_history
from domain.models import Cycle, DataWarning, Period, WarningKind
from domain.ports import PredictionConfig

CONFIG = PredictionConfig(period_length=5, cycle_length=28)


def _lengths(cycles: tuple[Cycle, ...]) -> list[int]:
    return [cycle.length_days for cycle in cycles]


def _kinds(history: History) -> list[WarningKind]:
    return [warning.kind for warning in history.warnings]


def test_three_starts_produce_two_lengths_oldest_first(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28])

    history = build_history(periods, CONFIG)

    assert _lengths(history.cycles) == [28, 28]
    assert [cycle.start for cycle in history.cycles] == [
        date(2026, 1, 1),
        date(2026, 1, 29),
    ]


def test_a_cycle_points_at_the_period_that_started_it(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28])

    history = build_history(periods, CONFIG)

    assert [cycle.period_id for cycle in history.cycles] == [
        periods[0].id,
        periods[1].id,
    ]


def test_an_open_period_contributes_no_cycle_length(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1), end=date(2026, 1, 5)),
        make_period(date(2026, 1, 29), end=date(2026, 2, 2)),
        make_period(date(2026, 3, 26)),
    ]

    history = build_history(periods, CONFIG)

    assert _lengths(history.cycles) == [28, 56]
    assert history.cycles[-1].start == date(2026, 1, 29)


def test_no_periods_yield_an_empty_history() -> None:
    history = build_history([], CONFIG)

    assert history.cycles == ()
    assert history.usable == ()
    assert history.warnings == ()


def test_unsorted_periods_are_derived_oldest_first(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 29])

    history = build_history(list(reversed(periods)), CONFIG)

    assert _lengths(history.cycles) == [28, 29]
    assert _lengths(history.usable) == [28, 29]


def test_a_long_cycle_is_excluded_and_reported(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 29, 75, 30])
    config = PredictionConfig(period_length=5, cycle_length=28, outlier_max_days=60)

    history = build_history(periods, config)

    assert _lengths(history.usable) == [28, 29, 30]
    assert _lengths(history.cycles) == [28, 29, 75, 30]
    outliers = [
        warning for warning in history.warnings if warning.kind is WarningKind.OUTLIER
    ]
    assert [warning.period_id for warning in outliers] == [periods[2].id]


def test_a_cycle_above_every_default_bound_is_reported_as_a_gap(
    make_periods: Callable[..., list[Period]],
) -> None:
    """Above 90 days a cycle is both out of range and a gap; the gap wins.

    The gap requirement excludes the boundary cycle *and* everything before it,
    so a 120-day cycle truncates the window rather than merely being skipped.
    """
    periods = make_periods([28, 29, 120, 30])

    history = build_history(periods, CONFIG)

    assert _lengths(history.cycles) == [28, 29, 120, 30]
    assert _lengths(history.usable) == [30]
    assert _kinds(history) == [WarningKind.GAP]
    assert history.warnings[0].period_id == periods[2].id


def test_a_short_cycle_is_excluded_and_reported(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 10, 29])

    history = build_history(periods, CONFIG)

    assert _lengths(history.usable) == [28, 29]
    outliers = [
        warning for warning in history.warnings if warning.kind is WarningKind.OUTLIER
    ]
    assert [warning.period_id for warning in outliers] == [periods[1].id]


def test_custom_bounds_replace_the_defaults(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([18, 30])
    config = PredictionConfig(period_length=5, cycle_length=28, outlier_min_days=20)

    history = build_history(periods, config)

    assert _lengths(history.usable) == [30]
    assert WarningKind.OUTLIER in _kinds(history)


def test_the_window_stops_at_the_most_recent_gap(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1)),
        make_period(date(2026, 1, 29)),
        make_period(date(2026, 2, 26)),
        make_period(date(2026, 9, 1)),
    ]

    history = build_history(periods, CONFIG)

    assert _lengths(history.cycles)[-1] == 187
    assert history.usable == ()
    gap_warnings = [
        warning for warning in history.warnings if warning.kind is WarningKind.GAP
    ]
    assert [warning.period_id for warning in gap_warnings] == [periods[2].id]


def test_the_gap_cycle_is_not_also_reported_as_an_outlier(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1)),
        make_period(date(2026, 1, 29)),
        make_period(date(2026, 9, 1)),
    ]

    history = build_history(periods, CONFIG)

    assert _kinds(history) == [WarningKind.GAP]


def test_cycles_before_the_gap_never_reach_the_window(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1)),
        make_period(date(2026, 1, 29)),
        make_period(date(2026, 2, 26)),
        make_period(date(2026, 9, 1)),
        make_period(date(2026, 9, 29)),
        make_period(date(2026, 10, 27)),
    ]

    history = build_history(periods, CONFIG)

    assert _lengths(history.cycles) == [28, 28, 187, 28, 28]
    assert _lengths(history.usable) == [28, 28]
    assert [cycle.start for cycle in history.usable] == [
        date(2026, 9, 1),
        date(2026, 9, 29),
    ]


def test_a_custom_gap_threshold_splits_a_shorter_break(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 40, 28])
    config = PredictionConfig(period_length=5, cycle_length=28, gap_days=30)

    history = build_history(periods, config)

    assert _lengths(history.usable) == [28]
    assert WarningKind.GAP in _kinds(history)


def test_filtering_happens_before_the_window(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([27, 28, 29, 28, 30, 28, 31, 29])

    history = build_history(periods, CONFIG)

    assert _lengths(history.usable) == [29, 28, 30, 28, 31, 29]


def test_an_excluded_cycle_does_not_occupy_a_window_slot(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 29, 30, 31, 32, 33, 75, 28])
    config = PredictionConfig(period_length=5, cycle_length=28, outlier_max_days=60)

    history = build_history(periods, config)

    assert _lengths(history.usable) == [29, 30, 31, 32, 33, 28]


def test_the_window_is_shorter_than_six_when_history_is_short(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([26, 30, 31])

    history = build_history(periods, CONFIG)

    assert _lengths(history.usable) == [26, 30, 31]


def test_a_history_window_of_zero_yields_no_usable_cycles(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 28])
    config = PredictionConfig(period_length=5, cycle_length=28, history_window=0)

    history = build_history(periods, config)

    assert history.usable == ()
    assert _lengths(history.cycles) == [28, 28]


def test_a_period_without_flow_is_reported(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1), flow=None),
        make_period(date(2026, 1, 29), flow="medium"),
    ]

    history = build_history(periods, CONFIG)

    assert history.warnings == (
        DataWarning(kind=WarningKind.MISSING_FLOW, period_id=periods[0].id),
    )
    assert _kinds(history) == [WarningKind.MISSING_FLOW]


def test_every_period_without_flow_is_reported(
    make_period: Callable[..., Period],
) -> None:
    periods = [
        make_period(date(2026, 1, 1), flow=None),
        make_period(date(2026, 1, 29), flow="light"),
        make_period(date(2026, 2, 26), flow=None),
    ]

    history = build_history(periods, CONFIG)

    missing = [
        warning
        for warning in history.warnings
        if warning.kind is WarningKind.MISSING_FLOW
    ]
    assert [warning.period_id for warning in missing] == [
        periods[0].id,
        periods[2].id,
    ]


def test_warnings_are_ordered_by_the_period_they_name(
    make_periods: Callable[..., list[Period]],
) -> None:
    periods = make_periods([28, 10, 29], flow=None)

    history = build_history(periods, CONFIG)

    assert _kinds(history) == [
        WarningKind.MISSING_FLOW,
        WarningKind.MISSING_FLOW,
        WarningKind.OUTLIER,
        WarningKind.MISSING_FLOW,
        WarningKind.MISSING_FLOW,
    ]
