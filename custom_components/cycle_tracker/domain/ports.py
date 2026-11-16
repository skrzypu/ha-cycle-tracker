"""Ports through which the domain reaches the outside world.

The domain never reads the wall clock and never persists anything: callers
supply a ``Clock`` and a ``PredictionConfig``, which keeps the pipeline a pure
function of periods, configuration and a reference date (ADR-0005).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable

DEFAULT_OUTLIER_MIN_DAYS = 15
DEFAULT_OUTLIER_MAX_DAYS = 90
DEFAULT_GAP_DAYS = 90
DEFAULT_HISTORY_WINDOW = 6


@dataclass(frozen=True)
class PredictionConfig:
    """Configuration the prediction pipeline reads.

    ``cycle_length`` is only used by the statistics fallback below two usable
    cycles; it is never a prediction fallback. The outlier bounds and the gap
    threshold default to the product rules in BDR-0004.
    """

    period_length: int
    cycle_length: int
    outlier_min_days: int = DEFAULT_OUTLIER_MIN_DAYS
    outlier_max_days: int = DEFAULT_OUTLIER_MAX_DAYS
    gap_days: int = DEFAULT_GAP_DAYS
    history_window: int = DEFAULT_HISTORY_WINDOW


@runtime_checkable
class Clock(Protocol):
    """Supplies the reference date for one calculation."""

    def today(self) -> date:
        """Return the current local date."""
        ...
