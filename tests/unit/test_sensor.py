"""Unit tests for Cycle Tracker sensors."""

import pytest
from datetime import date
from unittest.mock import MagicMock

from custom_components.cycle_tracker.sensor import (
    DaysUntilOvulationSensor,
    CycleDaySensor,
    CyclePhaseSensor,
    NextPeriodDateSensor,
    NextOvulationDateSensor,
    DaysUntilPeriodSensor,
    CycleStatisticsSensor,
)
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator
from custom_components.cycle_tracker.const import (
    DEFAULT_CYCLE_LENGTH,
    DEFAULT_PERIOD_LENGTH,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock(spec=CycleTrackerCoordinator)
    # Use a recent date so ovulation calculation produces a future date
    coordinator.get_last_period_start.return_value = "2026-10-01"
    coordinator.get_cycle_length.return_value = DEFAULT_CYCLE_LENGTH
    coordinator.get_period_length.return_value = DEFAULT_PERIOD_LENGTH
    coordinator.calculate_cycle_day.return_value = 14
    coordinator.calculate_phase.return_value = "ovulatory"
    coordinator.predict_next_period.return_value = "2026-10-29"
    coordinator.get_next_ovulation_date.return_value = "2026-10-15"
    coordinator.get_statistics.return_value = {
        "average_cycle_length": 28.0,
        "average_period_length": 5.0,
        "cycle_length_std_dev": 0.0,
        "period_length_std_dev": 0.0,
        "total_cycles_tracked": 3,
    }
    return coordinator


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {}
    return entry


class TestDaysUntilOvulationSensor:
    """Test DaysUntilOvulationSensor."""

    def test_native_value_returns_non_negative_int(self, mock_coordinator, mock_entry):
        """Test that native_value returns a non-negative int and raises no AttributeError."""
        sensor = DaysUntilOvulationSensor(mock_coordinator, mock_entry)
        value = sensor.native_value
        assert value is not None
        assert isinstance(value, int)
        assert value >= 0

    def test_native_value_no_last_period(self, mock_coordinator, mock_entry):
        """Test native_value returns None when no last period."""
        mock_coordinator.get_last_period_start.return_value = None
        sensor = DaysUntilOvulationSensor(mock_coordinator, mock_entry)
        assert sensor.native_value is None

    def test_native_value_no_ovulation_date(self, mock_coordinator, mock_entry):
        """Test native_value returns None when coordinator returns None."""
        mock_coordinator.get_next_ovulation_date.return_value = None
        sensor = DaysUntilOvulationSensor(mock_coordinator, mock_entry)
        assert sensor.native_value is None


class TestCycleDaySensor:
    """Test CycleDaySensor."""

    def test_native_value(self, mock_coordinator, mock_entry):
        """Test native_value returns cycle day."""
        sensor = CycleDaySensor(mock_coordinator, mock_entry)
        assert sensor.native_value == 14


class TestCyclePhaseSensor:
    """Test CyclePhaseSensor."""

    def test_native_value(self, mock_coordinator, mock_entry):
        """Test native_value returns cycle phase."""
        sensor = CyclePhaseSensor(mock_coordinator, mock_entry)
        assert sensor.native_value == "ovulatory"


class TestNextPeriodDateSensor:
    """Test NextPeriodDateSensor."""

    def test_native_value(self, mock_coordinator, mock_entry):
        """Test native_value returns next period date."""
        sensor = NextPeriodDateSensor(mock_coordinator, mock_entry)
        assert sensor.native_value == "2026-10-29"


class TestNextOvulationDateSensor:
    """Test NextOvulationDateSensor."""

    def test_native_value(self, mock_coordinator, mock_entry):
        """Test native_value returns next ovulation date (calculated by sensor)."""
        sensor = NextOvulationDateSensor(mock_coordinator, mock_entry)
        # Sensor calculates: last_start + cycle_length//2, advanced until >= today
        # last_start = 2026-10-01, cycle_length = 28, ovulation_offset = 14
        # 2026-10-01 + 14 = 2026-10-15 (if today <= 2026-10-15)
        assert sensor.native_value is not None
        parsed = date.fromisoformat(sensor.native_value)
        assert parsed >= date.today()


class TestDaysUntilPeriodSensor:
    """Test DaysUntilPeriodSensor."""

    def test_native_value(self, mock_coordinator, mock_entry):
        """Test native_value returns days until period."""
        sensor = DaysUntilPeriodSensor(mock_coordinator, mock_entry)
        assert sensor.native_value is not None
        assert isinstance(sensor.native_value, int)
        assert sensor.native_value >= 0


class TestCycleStatisticsSensor:
    """Test CycleStatisticsSensor."""

    def test_native_value(self, mock_coordinator, mock_entry):
        """Test native_value returns total cycles tracked."""
        sensor = CycleStatisticsSensor(mock_coordinator, mock_entry)
        assert sensor.native_value == 3

    def test_extra_state_attributes(self, mock_coordinator, mock_entry):
        """Test extra_state_attributes contains expected keys."""
        sensor = CycleStatisticsSensor(mock_coordinator, mock_entry)
        attrs = sensor.extra_state_attributes
        assert "average_cycle_length" in attrs
        assert "average_period_length" in attrs
        assert "std_dev_cycle" in attrs
        assert "std_dev_period" in attrs
        assert "total_cycles_tracked" in attrs
        assert "prediction_confidence" in attrs
