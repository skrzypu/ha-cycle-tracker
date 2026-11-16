"""End-to-end default strategy for an entry that never stored one.

The config entry owns the algorithm, but an entry created before that option
existed has no value in either ``data`` or ``options``. The coordinator then
falls back to the shipped default. This module deliberately overrides the
shared ``config_entry_data`` fixture without the algorithm key, because every
other end-to-end test stores ``weighted_moving_average`` explicitly and would
keep passing even if the default fell back to the arithmetic mean.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

import pytest

from custom_components.cycle_tracker.const import (
    ATTR_PREDICTED_CYCLE_LENGTH,
    ATTR_USABLE_CYCLE_COUNT,
    CONF_CYCLE_LENGTH,
    CONF_LAST_PERIOD_START,
    CONF_PERIOD_LENGTH,
)

NEXT_PERIOD = "sensor.cycle_tracker_next_period_date"

ClosedPeriod = Callable[..., Awaitable[None]]
LogPeriod = Callable[..., Awaitable[None]]


@pytest.fixture
def config_entry_data() -> dict[str, Any]:
    """Return settings from before the prediction algorithm was persisted."""
    return {
        CONF_CYCLE_LENGTH: 28,
        CONF_PERIOD_LENGTH: 5,
        CONF_LAST_PERIOD_START: "2026-01-01",
    }


async def test_an_entry_without_a_stored_algorithm_uses_the_weighted_average(
    closed_period: ClosedPeriod,
    log_period: LogPeriod,
    state_of,
) -> None:
    """The fallback setting is the weighted average, the shipped default.

    Cycle lengths 30 and 25 are enough to tell the strategies apart: weighted
    gives (1*30 + 2*25)/3 = 26.67 -> 27 and lands on 2026-12-07, while the
    arithmetic mean and the median both give 28 and would land on 2026-12-08.
    """
    await closed_period(date(2026, 9, 16))
    await closed_period(date(2026, 10, 16))
    await log_period(date(2026, 11, 10))

    next_period = state_of(NEXT_PERIOD)
    assert next_period.state == "2026-12-07"
    assert next_period.attributes[ATTR_PREDICTED_CYCLE_LENGTH] == 27
    assert next_period.attributes[ATTR_USABLE_CYCLE_COUNT] == 2
