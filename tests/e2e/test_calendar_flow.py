"""End-to-end calendar projection, read through the calendar service.

The calendar is a separate adapter with its own date maths (inclusive domain
ranges become exclusive calendar ranges), so it is asserted on the service
payload rather than on the domain events that produced it. The history is the
same three-period history as the sensor test: weighted 27-day cycle from
2026-11-10 puts the predicted period on 2026-12-07.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date

from custom_components.cycle_tracker.const import (
    ATTR_DAYS_LATE,
    ATTR_IS_LATE,
    ATTR_USABLE_CYCLE_COUNT,
)

DAYS_UNTIL_PERIOD = "sensor.cycle_tracker_days_until_period"
NEXT_PERIOD = "sensor.cycle_tracker_next_period_date"

ClosedPeriod = Callable[..., Awaitable[None]]
LogPeriod = Callable[..., Awaitable[None]]


def _summaries(events: list[dict[str, object]]) -> list[str]:
    """Return the event summaries in the order the service reported them."""
    return [str(event["summary"]) for event in events]


async def test_calendar_lists_recorded_and_projected_events(
    closed_period: ClosedPeriod,
    log_period: LogPeriod,
    calendar_events: Callable[[date, date], Awaitable[list[dict[str, object]]]],
) -> None:
    """A range holds the three recorded periods plus twelve projected cycles.

    The first projected cycle repeats the sensor prediction, and the payload
    uses the calendar's exclusive end dates, so the period from 2026-12-07 to
    2026-12-11 inclusive is reported as ending on 2026-12-12.
    """
    await closed_period(date(2026, 9, 16))
    await closed_period(date(2026, 10, 16))
    await log_period(date(2026, 11, 10))

    events = await calendar_events(date(2026, 9, 1), date(2027, 12, 31))

    summaries = _summaries(events)
    assert summaries.count("Period") == 3
    assert summaries.count("Predicted Period") == 12
    assert summaries.count("Ovulation") == 12
    assert summaries.count("Fertile Window") == 12

    starts = [str(event["start"]) for event in events]
    assert starts == sorted(starts)

    assert [(event["start"], event["end"]) for event in events[:6]] == [
        # Recorded periods, closed with a five-day bleeding window; the open
        # 2026-11-10 row is a single day because its end equals its start.
        ("2026-09-16", "2026-09-21"),
        ("2026-10-16", "2026-10-21"),
        ("2026-11-10", "2026-11-11"),
        # The projection steps from the predicted period: the first projected
        # cycle starts on 2026-12-07, so its ovulation centre is 14 days before
        # the following 27-day period, on 2026-12-20.
        ("2026-12-07", "2026-12-12"),
        ("2026-12-15", "2026-12-21"),
        ("2026-12-18", "2026-12-23"),
    ]
    assert [_summaries([event])[0] for event in events[:6]] == [
        "Period",
        "Period",
        "Period",
        "Predicted Period",
        "Fertile Window",
        "Ovulation",
    ]


async def test_calendar_keeps_a_late_prediction_on_its_frozen_date(
    closed_period: ClosedPeriod,
    log_period: LogPeriod,
    calendar_events: Callable[[date, date], Awaitable[list[dict[str, object]]]],
    state_of,
) -> None:
    """A late prediction stays on its old date instead of sliding to today.

    The two stable 28-day cycles predict 2026-11-09, four days before the
    frozen reference date. The sensor reports the late state, and the calendar
    still starts the projected series on 2026-11-09 — the automation's anchor
    does not move on its own.
    """
    await closed_period(date(2026, 8, 17))
    await closed_period(date(2026, 9, 14))
    await log_period(date(2026, 10, 12))

    events = await calendar_events(date(2026, 11, 1), date(2026, 12, 31))

    predicted = [event for event in events if event["summary"] == "Predicted Period"]
    assert [event["start"] for event in predicted] == ["2026-11-09", "2026-12-07"]

    days_until = state_of(DAYS_UNTIL_PERIOD)
    assert days_until.attributes[ATTR_IS_LATE] is True
    assert days_until.attributes[ATTR_DAYS_LATE] == 4
    assert state_of(NEXT_PERIOD).state == "2026-11-09"
    assert state_of(NEXT_PERIOD).attributes[ATTR_USABLE_CYCLE_COUNT] == 2
