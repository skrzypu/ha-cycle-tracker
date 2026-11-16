"""Projection of future cycle events (tasks 7.1-7.2)."""

from __future__ import annotations

from datetime import date, timedelta

from domain.events import CycleEvent, EventKind, project_events
from domain.models import ConfidenceBand, Prediction
from domain.ports import PredictionConfig

CONFIG = PredictionConfig(period_length=5, cycle_length=28)


def _prediction(
    next_period: date,
    cycle_length_days: int,
    is_late: bool = False,
) -> Prediction:
    ovulation_center = next_period - timedelta(days=14)
    return Prediction(
        next_period=next_period,
        cycle_length_days=cycle_length_days,
        uncertainty=(
            next_period - timedelta(days=2),
            next_period + timedelta(days=2),
        ),
        ovulation=(
            ovulation_center - timedelta(days=2),
            ovulation_center + timedelta(days=2),
        ),
        ovulation_center=ovulation_center,
        fertile=(ovulation_center - timedelta(days=5), ovulation_center),
        confidence=0.5,
        confidence_band=ConfidenceBand.MEDIUM,
        is_late=is_late,
        days_late=5 if is_late else 0,
        days_until_period=0,
        days_until_ovulation=0,
        warnings=(),
        usable_cycle_count=6,
    )


def _of_kind(events: tuple[CycleEvent, ...], kind: EventKind) -> list[CycleEvent]:
    return [event for event in events if event.kind is kind]


def test_twelve_cycles_project_three_events_each() -> None:
    events = project_events(_prediction(date(2026, 12, 1), 28), CONFIG)

    assert len(events) == 36
    assert len(_of_kind(events, EventKind.PERIOD)) == 12
    assert len(_of_kind(events, EventKind.OVULATION)) == 12
    assert len(_of_kind(events, EventKind.FERTILE)) == 12


def test_the_first_projected_period_starts_at_the_predicted_date() -> None:
    events = project_events(_prediction(date(2026, 12, 1), 28), CONFIG)

    assert _of_kind(events, EventKind.PERIOD)[0].start == date(2026, 12, 1)


def test_a_period_event_covers_the_configured_period_length() -> None:
    events = project_events(_prediction(date(2026, 12, 1), 28), CONFIG)

    first = _of_kind(events, EventKind.PERIOD)[0]

    assert first.start == date(2026, 12, 1)
    assert first.end == date(2026, 12, 5)


def test_each_cycle_steps_forward_by_the_predicted_length() -> None:
    events = project_events(_prediction(date(2026, 12, 1), 30), CONFIG)

    periods = _of_kind(events, EventKind.PERIOD)

    assert periods[1].start == date(2026, 12, 31)
    assert periods[2].start == date(2027, 1, 30)


def test_projection_uses_the_predicted_length_not_the_configured_one() -> None:
    config = PredictionConfig(period_length=5, cycle_length=99)

    events = project_events(_prediction(date(2026, 12, 1), 30), config)

    assert _of_kind(events, EventKind.PERIOD)[1].start == date(2026, 12, 31)


def test_windows_are_projected_with_each_period() -> None:
    events = project_events(_prediction(date(2026, 12, 1), 30), CONFIG)

    ovulation = [event for event in _of_kind(events, EventKind.OVULATION)]
    fertile = [event for event in _of_kind(events, EventKind.FERTILE)]

    assert (ovulation[0].start, ovulation[0].end) == (
        date(2026, 12, 15),
        date(2026, 12, 19),
    )
    assert (fertile[0].start, fertile[0].end) == (
        date(2026, 12, 12),
        date(2026, 12, 17),
    )


def test_each_cycle_windows_sit_inside_that_cycle() -> None:
    events = project_events(_prediction(date(2026, 12, 1), 30), CONFIG)

    for index, period in enumerate(_of_kind(events, EventKind.PERIOD)):
        next_start = period.start + timedelta(days=30)
        ovulation = _of_kind(events, EventKind.OVULATION)[index]
        fertile = _of_kind(events, EventKind.FERTILE)[index]
        assert period.start <= fertile.start <= ovulation.start <= next_start
        assert fertile.end <= next_start
        assert ovulation.end <= next_start


def test_a_late_prediction_is_projected_from_its_frozen_date() -> None:
    late = _prediction(date(2026, 12, 1), 30, is_late=True)

    events = project_events(late, CONFIG)

    assert _of_kind(events, EventKind.PERIOD)[0].start == date(2026, 12, 1)


def test_events_are_ordered_by_start_date() -> None:
    events = project_events(_prediction(date(2026, 12, 1), 30), CONFIG)

    starts = [event.start for event in events]

    assert starts == sorted(starts)


def test_a_custom_horizon_bounds_the_projection() -> None:
    events = project_events(_prediction(date(2026, 12, 1), 28), CONFIG, cycles=2)

    assert len(events) == 6


def test_a_horizon_of_zero_projects_nothing() -> None:
    assert project_events(_prediction(date(2026, 12, 1), 28), CONFIG, cycles=0) == ()
