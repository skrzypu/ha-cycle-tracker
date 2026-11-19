"""End-to-end period-open signal through the public services.

History enters only through the ``log_start``/``log_end`` services and the
result leaves only through the ``binary_sensor.cycle_tracker_period_open``
state, matching the boundary the rest of the e2e suite keeps.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, timedelta

PERIOD_OPEN = "binary_sensor.cycle_tracker_period_open"

LogPeriod = Callable[..., Awaitable[None]]


async def test_logging_a_period_opens_and_closes_the_period_open_sensor(
    log_period: LogPeriod,
    state_of,
) -> None:
    """``log_start`` turns the sensor on and ``log_end`` turns it off again."""
    start = date(2026, 11, 10)

    await log_period(start)
    assert state_of(PERIOD_OPEN).state == "on"

    await log_period(start, start + timedelta(days=4))
    assert state_of(PERIOD_OPEN).state == "off"
