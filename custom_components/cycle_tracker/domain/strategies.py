"""Prediction strategies and the registry that selects between them.

Strategies are plain callables over the usable cycle lengths, so a new
algorithm is one entry in ``STRATEGIES`` and nothing in the pipeline changes
(design decision 4). Every strategy returns whole days through
``round_half_up``, independently of Python's banker's rounding.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Sequence

_LOGGER = logging.getLogger(__name__)

ARITHMETIC_MEAN = "arithmetic_mean"
WEIGHTED_MOVING_AVERAGE = "weighted_moving_average"
MEDIAN = "median"

#: The strategy used when configuration is missing or names an unknown value.
DEFAULT_STRATEGY = WEIGHTED_MOVING_AVERAGE

_HALF_DAY = 0.5


def round_half_up(value: float) -> int:
    """Round to the nearest whole day, with halves rounding up."""
    return math.floor(value + _HALF_DAY)


def arithmetic_mean(lengths: Sequence[int]) -> int:
    """Average every usable cycle equally."""
    _require_lengths(lengths)
    return round_half_up(sum(lengths) / len(lengths))


def weighted_moving_average(lengths: Sequence[int]) -> int:
    """Average with weights 1..n, so the newest cycle weighs most."""
    _require_lengths(lengths)
    weights = range(1, len(lengths) + 1)
    weighted_sum = sum(weight * length for weight, length in zip(weights, lengths))
    return round_half_up(weighted_sum / sum(weights))


def median(lengths: Sequence[int]) -> int:
    """Return the middle length, rounding the mean of two middles half-up."""
    _require_lengths(lengths)
    ordered = sorted(lengths)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return round_half_up((ordered[middle - 1] + ordered[middle]) / 2)


STRATEGIES: dict[str, Callable[[Sequence[int]], int]] = {
    ARITHMETIC_MEAN: arithmetic_mean,
    WEIGHTED_MOVING_AVERAGE: weighted_moving_average,
    MEDIAN: median,
}


def get_strategy(name: str) -> Callable[[Sequence[int]], int]:
    """Return the named strategy, falling back to the default when unknown.

    The config flow validates the choice, so an unknown name means stored
    configuration drifted; a warning and the default keep the integration
    working instead of raising on every update.
    """
    try:
        return STRATEGIES[name]
    except KeyError:
        _LOGGER.warning(
            "Unknown prediction strategy %r, using %r", name, DEFAULT_STRATEGY
        )
        return STRATEGIES[DEFAULT_STRATEGY]


def _require_lengths(lengths: Sequence[int]) -> None:
    if not lengths:
        raise ValueError("Cannot predict a cycle length from an empty list")
