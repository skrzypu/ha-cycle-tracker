"""Unit tests for prediction algorithms."""

import pytest

from custom_components.cycle_tracker.prediction import (
    arithmetic_mean,
    weighted_moving_average,
    get_algorithm,
    validate_algorithm,
)
from custom_components.cycle_tracker.const import PREDICTION_ALGORITHMS


class TestArithmeticMean:
    """Test arithmetic_mean function."""

    def test_basic_mean(self):
        """Test basic arithmetic mean calculation."""
        assert arithmetic_mean([28, 28, 28]) == 28
        assert arithmetic_mean([28, 30]) == 29
        assert arithmetic_mean([25, 35]) == 30

    def test_rounding(self):
        """Test rounding behavior (Python uses banker's rounding)."""
        assert arithmetic_mean([28, 29]) == 28  # 28.5 -> 28 (banker's rounding)
        assert arithmetic_mean([28, 28, 29]) == 28  # 28.33 -> 28

    def test_single_value(self):
        """Test with single cycle length."""
        assert arithmetic_mean([28]) == 28

    def test_empty_list_raises(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError):
            arithmetic_mean([])


class TestWeightedMovingAverage:
    """Test weighted_moving_average function."""

    def test_basic_wma(self):
        """Test basic WMA calculation."""
        # Oldest to newest: [28, 30, 32]
        # Weights: 1, 2, 3
        # (1*28 + 2*30 + 3*32) / (1+2+3) = (28 + 60 + 96) / 6 = 184/6 = 30.67 -> 31
        assert weighted_moving_average([28, 30, 32]) == 31

    def test_wma_differs_from_mean(self):
        """Test case where WMA differs from arithmetic mean due to newest-heavy weighting."""
        # Recent cycles getting longer: [28, 28, 35]
        # Mean: (28+28+35)/3 = 30.33 -> 30
        # WMA: (1*28 + 2*28 + 3*35) / 6 = (28+56+105)/6 = 189/6 = 31.5 -> 32
        assert arithmetic_mean([28, 28, 35]) == 30
        assert weighted_moving_average([28, 28, 35]) == 32

    def test_equal_values(self):
        """Test WMA with all equal values."""
        assert weighted_moving_average([28, 28, 28]) == 28

    def test_two_values(self):
        """Test WMA with two values."""
        # Weights: 1, 2
        # (1*28 + 2*30) / 3 = 88/3 = 29.33 -> 29
        assert weighted_moving_average([28, 30]) == 29

    def test_single_value(self):
        """Test with single cycle length."""
        assert weighted_moving_average([28]) == 28

    def test_empty_list_raises(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError):
            weighted_moving_average([])


class TestAlgorithmSelector:
    """Test get_algorithm and validate_algorithm functions."""

    def test_get_arithmetic_mean(self):
        """Test getting arithmetic_mean algorithm."""
        algo = get_algorithm("arithmetic_mean")
        assert algo is arithmetic_mean
        assert algo([28, 30]) == 29

    def test_get_weighted_moving_average(self):
        """Test getting weighted_moving_average algorithm."""
        algo = get_algorithm("weighted_moving_average")
        assert algo is weighted_moving_average
        assert algo([28, 30]) == 29

    def test_get_unknown_fallback(self):
        """Test unknown algorithm falls back to WMA."""
        algo = get_algorithm("unknown")
        assert algo is weighted_moving_average

    def test_validate_known_algorithms(self):
        """Test validation of known algorithms."""
        for name in PREDICTION_ALGORITHMS:
            assert validate_algorithm(name) is True

    def test_validate_unknown_algorithm(self):
        """Test validation of unknown algorithm."""
        assert validate_algorithm("unknown") is False
        assert validate_algorithm("") is False