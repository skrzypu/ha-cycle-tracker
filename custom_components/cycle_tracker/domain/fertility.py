"""Uncertainty-aware fertility estimate derived from the existing prediction.

The six-day fertile window is not recomputed here. This module only presents its
uncertainty: the margin comes from the same population σ that feeds the period
window and the confidence score, and the extended bands are projected from the
prediction's current and next ovulation. ``fertility_estimate`` is a pure
function of its arguments — it never reads the clock and never persists anything
(ADR-0001/0005/0006).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from .models import ConfidenceBand, Prediction
from .statistics import MINIMUM_USABLE_CYCLES, CycleStatistics

#: The margin never narrows below this, even for perfectly regular cycles.
MIN_FERTILITY_MARGIN_DAYS = 2


class FertilityState(StrEnum):
    """Stable technical states of the fertility estimate.

    These values are identifiers, never user-facing copy; translations map them
    to labels so the domain stays free of wording (design decision 5).
    """

    OUTSIDE_ESTIMATED_FERTILE_WINDOW = "outside_estimated_fertile_window"
    WITHIN_ESTIMATED_FERTILE_WINDOW = "within_estimated_fertile_window"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FertilityEstimate:
    """The estimated fertile window with its uncertainty made explicit."""

    state: FertilityState
    #: The unchanged six-day window of the cycle shown with the estimate.
    fertile_window: tuple[date, date] | None
    #: The window widened by ``margin_days`` on each side.
    margin_band: tuple[date, date] | None
    margin_days: int
    confidence: float | None
    confidence_band: ConfidenceBand | None
    usable_cycle_count: int
    #: The passed cycle's band, present only in the outside state when it ended
    #: before the reference date.
    previous_margin_band: tuple[date, date] | None = None
    #: The upcoming cycle's band, present only in the outside state when it
    #: starts after the reference date.
    next_margin_band: tuple[date, date] | None = None
    #: Whole days from the previous band's inclusive end to the reference date;
    #: absent when there is no previous band or the state is within/unknown.
    previous_band_days_ago: int | None = None


def fertility_estimate(
    prediction: Prediction | None,
    statistics: CycleStatistics,
    today: date,
) -> FertilityEstimate:
    """Classify ``today`` against the estimated window of the current cycle.

    Two bands are considered: the running cycle's and the first ovulation that
    has not passed yet (``Prediction.next_ovulation``). Neither band is clamped
    to its cycle start — they express uncertainty about an ovulation that can
    fall near a boundary, so clamping would fake precision.
    """
    if prediction is None or prediction.usable_cycle_count < MINIMUM_USABLE_CYCLES:
        return FertilityEstimate(
            state=FertilityState.UNKNOWN,
            fertile_window=None,
            margin_band=None,
            previous_margin_band=None,
            next_margin_band=None,
            previous_band_days_ago=None,
            margin_days=0,
            confidence=statistics.confidence,
            confidence_band=statistics.confidence_band,
            usable_cycle_count=(
                prediction.usable_cycle_count if prediction is not None else 0
            ),
        )

    margin = max(MIN_FERTILITY_MARGIN_DAYS, math.ceil(statistics.cycle_length_std_dev))
    offset = timedelta(days=margin)
    current_band = (
        prediction.fertile[0] - offset,
        prediction.ovulation_center + offset,
    )
    next_band = (
        prediction.next_ovulation.fertile[0] - offset,
        prediction.next_ovulation.ovulation_center + offset,
    )

    # The band shown alongside the state is the one that applies to the
    # reference date when it is inside a band, otherwise the upcoming one.
    if _contains(current_band, today):
        state = FertilityState.WITHIN_ESTIMATED_FERTILE_WINDOW
        fertile_window = prediction.fertile
        margin_band = current_band
    elif _contains(next_band, today):
        state = FertilityState.WITHIN_ESTIMATED_FERTILE_WINDOW
        fertile_window = prediction.next_ovulation.fertile
        margin_band = next_band
    else:
        state = FertilityState.OUTSIDE_ESTIMATED_FERTILE_WINDOW
        fertile_window = prediction.next_ovulation.fertile
        margin_band = next_band

    # Both gap edges are reported only in the outside state. Each is omitted
    # when the band does not genuinely lie on that side of the reference date,
    # and is never duplicated from the other edge (design decision 2).
    previous_margin_band = None
    next_margin_band = None
    previous_band_days_ago = None
    if state == FertilityState.OUTSIDE_ESTIMATED_FERTILE_WINDOW:
        if current_band[1] < today:
            previous_margin_band = current_band
            previous_band_days_ago = (today - current_band[1]).days
        if next_band[0] > today:
            next_margin_band = next_band

    return FertilityEstimate(
        state=state,
        fertile_window=fertile_window,
        margin_band=margin_band,
        previous_margin_band=previous_margin_band,
        next_margin_band=next_margin_band,
        previous_band_days_ago=previous_band_days_ago,
        margin_days=margin,
        confidence=statistics.confidence,
        confidence_band=statistics.confidence_band,
        usable_cycle_count=prediction.usable_cycle_count,
    )


def _contains(band: tuple[date, date], reference_date: date) -> bool:
    """Whether the inclusive band covers the reference date."""
    return band[0] <= reference_date <= band[1]
