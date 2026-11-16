"""Projection of future cycle events from a frozen prediction.

The calendar must not be a second prediction: events step forward from the
predicted next period by the predicted cycle length, even when that date is in
the past, so a late period never shifts the calendar silently. Each projected
cycle contributes its period, its ovulation window and its fertile window
(BDR-0004).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from .models import Prediction
from .ports import PredictionConfig
from .windows import cycle_windows

#: How many cycles ahead the calendar projects by default.
DEFAULT_PROJECTION_CYCLES = 12

_KIND_ORDER = {"period": 0, "fertile": 1, "ovulation": 2}


class EventKind(StrEnum):
    """Kinds of cycle event the calendar can show."""

    PERIOD = "period"
    OVULATION = "ovulation"
    FERTILE = "fertile"


@dataclass(frozen=True)
class CycleEvent:
    """A date range whose ``end`` is the inclusive last day."""

    kind: EventKind
    start: date
    end: date


def project_events(
    prediction: Prediction,
    config: PredictionConfig,
    cycles: int = DEFAULT_PROJECTION_CYCLES,
) -> tuple[CycleEvent, ...]:
    """Project ``cycles`` future cycles and their windows from a prediction."""
    events: list[CycleEvent] = []
    for index in range(max(cycles, 0)):
        cycle_start = prediction.next_period + timedelta(
            days=prediction.cycle_length_days * index
        )
        windows = cycle_windows(
            cycle_start, prediction.cycle_length_days, config.period_length
        )
        events.append(
            CycleEvent(EventKind.PERIOD, windows.period_start, windows.period_end)
        )
        events.append(
            CycleEvent(EventKind.FERTILE, windows.fertile[0], windows.fertile[1])
        )
        events.append(
            CycleEvent(EventKind.OVULATION, windows.ovulation[0], windows.ovulation[1])
        )
    events.sort(key=lambda event: (event.start, event.end, _KIND_ORDER[event.kind]))
    return tuple(events)
