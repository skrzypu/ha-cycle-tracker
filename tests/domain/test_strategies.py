"""Prediction strategies and their registry (tasks 4.1-4.3)."""

from __future__ import annotations

import logging
from collections.abc import Callable

import pytest
from domain.strategies import (
    ARITHMETIC_MEAN,
    DEFAULT_STRATEGY,
    MEDIAN,
    STRATEGIES,
    WEIGHTED_MOVING_AVERAGE,
    arithmetic_mean,
    get_strategy,
    median,
    round_half_up,
    weighted_moving_average,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (28.0, 28),
        (28.4, 28),
        (28.5, 29),
        (27.5, 28),
        (29.5, 30),
    ],
)
def test_round_half_up_never_uses_bankers_rounding(value: float, expected: int) -> None:
    assert round_half_up(value) == expected


def test_round_half_up_is_not_pythons_round() -> None:
    assert round(28.5) != round_half_up(28.5)


def test_arithmetic_mean_averages_equally() -> None:
    assert arithmetic_mean([26, 30, 31]) == 29


def test_arithmetic_mean_rounds_half_up() -> None:
    assert arithmetic_mean([28, 29]) == 29


def test_weighted_moving_average_weights_the_newest_cycle_most() -> None:
    # 26 * 1 + 30 * 2 = 86, / 3 = 28.67 -> 29
    assert weighted_moving_average([26, 30]) == 29


def test_weighted_moving_average_sits_above_the_arithmetic_mean() -> None:
    lengths = [20, 20, 40]

    assert weighted_moving_average(lengths) > arithmetic_mean(lengths)


def test_weighted_moving_average_of_equal_lengths_is_that_length() -> None:
    assert weighted_moving_average([28, 28, 28]) == 28


def test_median_of_an_odd_count_is_the_middle_value() -> None:
    # sorted: 25, 31, 40
    assert median([31, 25, 40]) == 31


def test_median_of_an_even_count_rounds_the_two_middle_values() -> None:
    # sorted: 26, 27, 30, 31 -> (27 + 30) / 2 = 28.5 -> 29
    assert median([26, 30, 31, 27]) == 29


def test_median_of_an_even_count_rounds_half_up() -> None:
    assert median([26, 27]) == 27


def test_the_registry_exposes_the_three_strategies() -> None:
    assert set(STRATEGIES) == {
        ARITHMETIC_MEAN,
        WEIGHTED_MOVING_AVERAGE,
        MEDIAN,
    }
    assert STRATEGIES[ARITHMETIC_MEAN] is arithmetic_mean
    assert STRATEGIES[WEIGHTED_MOVING_AVERAGE] is weighted_moving_average
    assert STRATEGIES[MEDIAN] is median


def test_the_default_strategy_is_the_weighted_moving_average() -> None:
    assert DEFAULT_STRATEGY == WEIGHTED_MOVING_AVERAGE
    assert get_strategy(DEFAULT_STRATEGY) is weighted_moving_average


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (ARITHMETIC_MEAN, arithmetic_mean),
        (WEIGHTED_MOVING_AVERAGE, weighted_moving_average),
        (MEDIAN, median),
    ],
)
def test_get_strategy_returns_the_named_strategy(
    name: str, expected: Callable[[list[int]], int]
) -> None:
    assert get_strategy(name) is expected


def test_an_unknown_strategy_falls_back_to_the_default_with_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        strategy = get_strategy("holt_winters")

    assert strategy is weighted_moving_average
    assert any(
        record.levelno is logging.WARNING and "holt_winters" in record.message
        for record in caplog.records
    )


@pytest.mark.parametrize(
    "strategy",
    [arithmetic_mean, weighted_moving_average, median],
)
def test_a_strategy_refuses_an_empty_history(
    strategy: Callable[[list[int]], int],
) -> None:
    with pytest.raises(ValueError, match="empty"):
        strategy([])
