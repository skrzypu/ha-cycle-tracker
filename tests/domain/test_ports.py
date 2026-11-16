"""Ports the domain is handed (task 2.2)."""

from __future__ import annotations

import dataclasses
from datetime import date

import pytest
from domain.ports import Clock, PredictionConfig


class FixedClock:
    """A clock frozen on one date, standing in for the Home Assistant clock."""

    def __init__(self, reference_date: date) -> None:
        self._reference_date = reference_date

    def today(self) -> date:
        return self._reference_date


def test_a_fixed_clock_satisfies_the_clock_protocol() -> None:
    clock = FixedClock(date(2026, 11, 13))

    assert isinstance(clock, Clock)
    assert clock.today() == date(2026, 11, 13)


def test_prediction_config_defaults_are_the_product_rules() -> None:
    config = PredictionConfig(period_length=5, cycle_length=28)

    assert config.outlier_min_days == 15
    assert config.outlier_max_days == 90
    assert config.gap_days == 90
    assert config.history_window == 6


def test_prediction_config_can_override_every_bound() -> None:
    config = PredictionConfig(
        period_length=4,
        cycle_length=30,
        outlier_min_days=20,
        outlier_max_days=45,
        gap_days=60,
        history_window=3,
    )

    assert config.outlier_min_days == 20
    assert config.outlier_max_days == 45
    assert config.gap_days == 60
    assert config.history_window == 3


def test_prediction_config_is_frozen() -> None:
    config = PredictionConfig(period_length=5, cycle_length=28)

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.cycle_length = 30  # type: ignore[misc]
