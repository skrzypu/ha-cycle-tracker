"""End-to-end period-open signal through the public services.

History enters only through the ``log_start``/``log_end`` services and the
result leaves only through the ``binary_sensor.cycle_tracker_period_open``
state, matching the boundary the rest of the e2e suite keeps.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from custom_components.cycle_tracker.const import ATTR_TOTAL_CYCLES_TRACKED

PERIOD_OPEN = "binary_sensor.cycle_tracker_period_open"
STATISTICS = "sensor.cycle_tracker_statistics"

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


async def test_same_day_repeat_updates_the_open_row_instead_of_appending(
    log_period: LogPeriod,
    sheet_emulator: Any,
    state_of,
) -> None:
    """A same-day ``log_start`` must update the open row, not append a second one.

    Regression: logging the same start date twice reuses the latest period's
    ``period_id`` and rewrites that row in place with the new flow. Treating the
    two calls as distinct periods would leave two rows for one day and make the
    sensors report two tracked periods.
    """
    start = date(2026, 11, 10)

    await log_period(start, flow="light")
    first_rows = sheet_emulator.rows
    assert len(first_rows) == 1
    first_period_id = first_rows[0][0]

    await log_period(start, flow="heavy")

    # The public entities still show exactly one, still-open period.
    statistics = state_of(STATISTICS)
    assert statistics.attributes[ATTR_TOTAL_CYCLES_TRACKED] == 1
    assert state_of(PERIOD_OPEN).state == "on"

    # The sheet holds one row: the same period_id and start date, the last flow
    # value, and an empty end date. No duplicate row was appended.
    rows = sheet_emulator.rows
    assert len(rows) == 1
    row = rows[0]
    assert UUID(row[0])  # period_id
    assert row[0] == first_period_id
    assert row[1] == start.isoformat()
    assert row[2] == ""
    assert row[3] == "heavy"
