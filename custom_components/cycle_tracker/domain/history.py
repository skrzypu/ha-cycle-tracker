"""Derive cycle lengths and the usable history window from recorded periods.

A cycle is a start-to-start length, so an open period never contributes one.
Filtering happens before the window: out-of-range cycles and everything at or
before the most recent long gap are removed first, and an excluded cycle never
takes one of the window slots. Prediction and statistics both read the same
``History``, so their view of the data cannot diverge (design decision 3).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from uuid import UUID

from .models import Cycle, DataWarning, Period, WarningKind
from .ports import PredictionConfig


@dataclass(frozen=True)
class History:
    """All derived cycles plus the window prediction and statistics share.

    ``cycles`` keeps every cycle, including outliers and history before a gap;
    ``usable`` is the filtered, gap-truncated, most recent window.
    """

    cycles: tuple[Cycle, ...]
    usable: tuple[Cycle, ...]
    warnings: tuple[DataWarning, ...]


def build_history(periods: Sequence[Period], config: PredictionConfig) -> History:
    """Derive cycles, warnings and the usable window from recorded periods.

    A cycle that crosses a long gap is reported as a gap, never also as an
    outlier: the gap is the reason it is unusable. Every warning names the
    period that begins the affected cycle, except ``missing_flow``, which names
    the period itself.
    """
    ordered = tuple(sorted(periods, key=lambda period: period.start))
    cycles = _derive_cycles(ordered)
    gap_index = _latest_gap_index(cycles, config.gap_days)
    warnings = _collect_warnings(ordered, cycles, gap_index, config)

    after_gap = cycles[gap_index + 1 :] if gap_index is not None else cycles
    in_range = tuple(cycle for cycle in after_gap if _within_bounds(cycle, config))
    window = max(config.history_window, 0)
    usable = in_range[-window:] if window else ()

    return History(cycles=cycles, usable=usable, warnings=warnings)


def _derive_cycles(ordered: Sequence[Period]) -> tuple[Cycle, ...]:
    """Lengths between consecutive starts, oldest first.

    Only start dates matter, so a period without an end date contributes no
    length until the next start is recorded.
    """
    return tuple(
        Cycle(
            start=earlier.start,
            length_days=(later.start - earlier.start).days,
            period_id=earlier.id,
        )
        for earlier, later in pairwise(ordered)
    )


def _latest_gap_index(cycles: Sequence[Cycle], gap_days: int) -> int | None:
    """Index of the most recent cycle longer than the gap threshold, if any."""
    latest: int | None = None
    for index, cycle in enumerate(cycles):
        if cycle.length_days > gap_days:
            latest = index
    return latest


def _within_bounds(cycle: Cycle, config: PredictionConfig) -> bool:
    return config.outlier_min_days <= cycle.length_days <= config.outlier_max_days


def _collect_warnings(
    ordered: Sequence[Period],
    cycles: Sequence[Cycle],
    gap_index: int | None,
    config: PredictionConfig,
) -> tuple[DataWarning, ...]:
    found: list[tuple[date, WarningKind, UUID]] = []
    for period in ordered:
        if not period.flow:
            found.append((period.start, WarningKind.MISSING_FLOW, period.id))
    for index, cycle in enumerate(cycles):
        if index == gap_index:
            found.append((cycle.start, WarningKind.GAP, cycle.period_id))
        elif not _within_bounds(cycle, config):
            found.append((cycle.start, WarningKind.OUTLIER, cycle.period_id))

    found.sort(key=lambda item: (item[0], item[1].value))
    return tuple(
        DataWarning(kind=kind, period_id=period_id) for _start, kind, period_id in found
    )
