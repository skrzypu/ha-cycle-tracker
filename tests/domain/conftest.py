"""Fixtures shared by the framework-free domain tests.

The domain package lives inside the Home Assistant integration, so importing it
as ``custom_components.cycle_tracker.domain`` would execute the integration's
``__init__`` and pull Home Assistant in. The integration directory is put on
``sys.path`` instead and the tests import ``domain`` directly, which keeps them
runnable in plain Python as ADR-0005 requires.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import pytest

INTEGRATION_DIR = (
    Path(__file__).resolve().parents[2] / "custom_components" / "cycle_tracker"
)
if str(INTEGRATION_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_DIR))

from domain.models import Period, legacy_period_id  # noqa: E402

FIRST_START = date(2026, 1, 1)


@pytest.fixture
def make_period() -> Callable[..., Period]:
    """Build a period whose id is the stable id of its start date."""

    def _make(
        start: date,
        end: date | None = None,
        flow: str | None = "medium",
    ) -> Period:
        return Period(id=legacy_period_id(start), start=start, end=end, flow=flow)

    return _make


@pytest.fixture
def make_periods(
    make_period: Callable[..., Period],
) -> Callable[..., list[Period]]:
    """Build consecutive periods from the cycle lengths between their starts."""

    def _make(
        lengths: list[int],
        first: date = FIRST_START,
        flow: str | None = "medium",
    ) -> list[Period]:
        starts = [first]
        for length in lengths:
            starts.append(starts[-1] + timedelta(days=length))
        return [make_period(start, flow=flow) for start in starts]

    return _make
