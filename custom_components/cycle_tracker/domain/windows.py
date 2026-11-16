"""Geometry of the prediction windows.

The ovulation centre, its ±2-day window and the six-day fertile window are
computed here once, because both the prediction of the current cycle and the
projection of future cycles need exactly the same shape. Windows are clamped to
the cycle start so they never reach into the preceding cycle (BDR-0004).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

#: The ovulation centre sits this many days before the next period start.
OVULATION_LEAD_DAYS = 14
#: The ovulation window is the centre plus and minus this many days.
OVULATION_WINDOW_HALF_WIDTH_DAYS = 2
#: The fertile window starts this many days before the ovulation centre.
FERTILE_LEAD_DAYS = 5


@dataclass(frozen=True)
class CycleWindows:
    """Window dates for one cycle, from its start to its next period."""

    period_start: date
    period_end: date
    next_period: date
    ovulation_center: date
    ovulation: tuple[date, date]
    fertile: tuple[date, date]


def cycle_windows(
    cycle_start: date, cycle_length_days: int, period_length: int
) -> CycleWindows:
    """Compute the period, ovulation and fertile windows of one cycle."""
    next_period = cycle_start + timedelta(days=cycle_length_days)
    center = next_period - timedelta(days=OVULATION_LEAD_DAYS)
    bleeding_days = max(period_length - 1, 0)
    return CycleWindows(
        period_start=cycle_start,
        period_end=cycle_start + timedelta(days=bleeding_days),
        next_period=next_period,
        ovulation_center=center,
        ovulation=(
            max(center - timedelta(days=OVULATION_WINDOW_HALF_WIDTH_DAYS), cycle_start),
            center + timedelta(days=OVULATION_WINDOW_HALF_WIDTH_DAYS),
        ),
        fertile=(
            max(center - timedelta(days=FERTILE_LEAD_DAYS), cycle_start),
            center,
        ),
    )
