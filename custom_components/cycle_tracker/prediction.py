"""Prediction algorithms for cycle length estimation."""

from typing import Callable

from .const import PREDICTION_ALGORITHMS


def arithmetic_mean(lengths: list[int]) -> int:
    """Calculate arithmetic mean of cycle lengths, rounded to nearest integer."""
    if not lengths:
        raise ValueError("Cannot calculate mean of empty list")
    return round(sum(lengths) / len(lengths))


def weighted_moving_average(lengths: list[int]) -> int:
    """Calculate weighted moving average with newest weighted highest.

    Weights: index i (0-based, oldest first) gets weight i+1.
    """
    if not lengths:
        raise ValueError("Cannot calculate WMA of empty list")
    total_weight = sum(i + 1 for i in range(len(lengths)))
    weighted_sum = sum((i + 1) * length for i, length in enumerate(lengths))
    return round(weighted_sum / total_weight)


def get_algorithm(algorithm_name: str) -> Callable[[list[int]], int]:
    """Get prediction algorithm function by name."""
    if algorithm_name == "arithmetic_mean":
        return arithmetic_mean
    if algorithm_name == "weighted_moving_average":
        return weighted_moving_average
    # Fallback to default (should not happen if config is validated)
    return weighted_moving_average


def validate_algorithm(algorithm_name: str) -> bool:
    """Validate that algorithm name is supported."""
    return algorithm_name in PREDICTION_ALGORITHMS