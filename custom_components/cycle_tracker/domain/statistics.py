"""Cycle statistics from the same usable window the prediction reads.

Cycle-length statistics describe the filtered, gap-truncated six-cycle window;
period-length statistics use completed periods only. Below two usable cycles the
configured lengths stand in, with zero deviations, so the sensors degrade
gracefully instead of reporting a one-sample average as if it were measured.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

# The absolute import below resolves to the standard library even though this
# module shares its name: the package directory itself is never on sys.path.
from statistics import fmean, pstdev

from .history import History
from .models import ConfidenceBand, Period
from .ports import PredictionConfig

#: Fewer usable cycles than this yields no prediction and no confidence.
MINIMUM_USABLE_CYCLES = 2

CONFIDENCE_LOW_BELOW = 0.4
CONFIDENCE_HIGH_ABOVE = 0.7


@dataclass(frozen=True)
class CycleStatistics:
    """Everything the statistics sensor reports."""

    average_cycle_length: float
    average_period_length: float
    cycle_length_std_dev: float
    period_length_std_dev: float
    total_cycles_tracked: int
    shortest_cycle: int
    longest_cycle: int
    confidence: float | None
    confidence_band: ConfidenceBand | None


def statistics(
    periods: Sequence[Period], history: History, config: PredictionConfig
) -> CycleStatistics:
    """Summarize the periods and the usable cycle window they produced.

    ``total_cycles_tracked`` counts recorded periods, open one included, because
    that is what the user has logged — lengths are derived, periods are stored.
    """
    usable_lengths = [cycle.length_days for cycle in history.usable]
    average, deviation, shortest, longest = _cycle_measures(usable_lengths, config)
    period_lengths = _completed_period_lengths(periods)
    average_period, period_deviation = _period_measures(period_lengths, config)

    score: float | None = None
    band: ConfidenceBand | None = None
    if len(usable_lengths) >= MINIMUM_USABLE_CYCLES:
        score = confidence_score(
            mean=average,
            sigma=deviation,
            count=len(usable_lengths),
            target=config.history_window,
        )
        band = confidence_band(score)

    return CycleStatistics(
        average_cycle_length=average,
        average_period_length=average_period,
        cycle_length_std_dev=deviation,
        period_length_std_dev=period_deviation,
        total_cycles_tracked=len(periods),
        shortest_cycle=shortest,
        longest_cycle=longest,
        confidence=score,
        confidence_band=band,
    )


def confidence_score(mean: float, sigma: float, count: int, target: int) -> float:
    """How much of the history supports the prediction, from 0 to 1.

    ``min(1, 1 - sigma / mean) * min(1, n / target)``: it rises as cycles become
    regular and as more of them are recorded, and it describes the data rather
    than the chosen strategy (BDR-0004).
    """
    if mean <= 0:
        return 0.0
    stability = min(1.0, max(0.0, 1.0 - sigma / mean))
    volume = min(1.0, max(0.0, count / target)) if target > 0 else 1.0
    return stability * volume


def confidence_band(score: float) -> ConfidenceBand:
    """Band the score: low below 0.4, high above 0.7, medium in between."""
    if score < CONFIDENCE_LOW_BELOW:
        return ConfidenceBand.LOW
    if score > CONFIDENCE_HIGH_ABOVE:
        return ConfidenceBand.HIGH
    return ConfidenceBand.MEDIUM


def _cycle_measures(
    lengths: Sequence[int], config: PredictionConfig
) -> tuple[float, float, int, int]:
    """Average, population deviation, shortest and longest usable cycle."""
    if len(lengths) < MINIMUM_USABLE_CYCLES:
        return (
            float(config.cycle_length),
            0.0,
            config.cycle_length,
            config.cycle_length,
        )
    return fmean(lengths), pstdev(lengths), min(lengths), max(lengths)


def _completed_period_lengths(periods: Sequence[Period]) -> list[int]:
    """Bleeding days of closed periods; malformed rows are skipped, not fatal."""
    lengths: list[int] = []
    for period in periods:
        if period.end is None or period.end < period.start:
            continue
        lengths.append((period.end - period.start).days + 1)
    return lengths


def _period_measures(
    lengths: Sequence[int], config: PredictionConfig
) -> tuple[float, float]:
    if not lengths:
        return float(config.period_length), 0.0
    return fmean(lengths), pstdev(lengths)
