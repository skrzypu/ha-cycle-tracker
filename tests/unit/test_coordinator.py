"""Unit tests for CycleTrackerCoordinator."""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.data = {
        "cycle_length": 28,
        "period_length": 5,
        "last_period_start": "2024-01-01",
        "prediction_algorithm": "weighted_moving_average",
        "notification_offset_days": 2,
        "enable_notifications": False,
        "notification_time": "08:00",
    }
    entry.entry_id = "test_entry_id"
    return entry


@pytest.fixture
def mock_store():
    """Create a mock store."""
    store = AsyncMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    return store


@pytest.fixture
def coordinator(mock_hass, mock_entry, mock_store):
    """Create a coordinator instance with mocked dependencies."""
    with patch(
        "custom_components.cycle_tracker.coordinator.Store", return_value=mock_store
    ):
        coord = CycleTrackerCoordinator(mock_hass, mock_entry)
        coord.store = mock_store
        return coord


class TestCycleTrackerCoordinator:
    """Test the CycleTrackerCoordinator class."""

    def test_init(self, coordinator, mock_entry):
        """Test coordinator initialization."""
        assert coordinator.entry == mock_entry
        assert coordinator._data == {}

    def test_get_default_data(self, coordinator):
        """Test default data structure."""
        data = coordinator._get_default_data()
        assert data["periods"] == []
        assert data["cycle_length"] == 28
        assert data["period_length"] == 5
        assert data["last_period_start"] == "2024-01-01"
        assert data["prediction_algorithm"] == "weighted_moving_average"
        assert data["notification_offset_days"] == 2
        assert data["enable_notifications"] is False
        assert data["notification_time"] == "08:00"

    @pytest.mark.asyncio
    async def test_async_update_data_no_stored_data(self, coordinator, mock_store):
        """Test loading data when no stored data exists."""
        mock_store.async_load.return_value = None
        data = await coordinator._async_update_data()
        assert data["periods"] == []
        assert data["cycle_length"] == 28

    @pytest.mark.asyncio
    async def test_async_update_data_with_stored_data(self, coordinator, mock_store):
        """Test loading data when stored data exists."""
        stored_data = {
            "periods": [{"start_date": "2024-01-01", "end_date": "2024-01-05"}],
            "cycle_length": 30,
        }
        mock_store.async_load.return_value = stored_data
        data = await coordinator._async_update_data()
        assert data["periods"] == stored_data["periods"]
        assert data["cycle_length"] == 30

    def test_get_periods(self, coordinator):
        """Test getting periods."""
        coordinator._data = {"periods": [{"start_date": "2024-01-01"}]}
        periods = coordinator.get_periods()
        assert len(periods) == 1
        assert periods[0]["start_date"] == "2024-01-01"

    def test_add_period(self, coordinator):
        """Test adding a period."""
        coordinator._data = {"periods": []}
        coordinator.add_period({"start_date": "2024-02-01", "end_date": "2024-02-05"})
        periods = coordinator.get_periods()
        assert len(periods) == 1
        assert periods[0]["start_date"] == "2024-02-01"

    def test_add_period_sorts(self, coordinator):
        """Test that periods are sorted by start date."""
        coordinator._data = {
            "periods": [{"start_date": "2024-02-01", "end_date": "2024-02-05"}]
        }
        coordinator.add_period({"start_date": "2024-01-01", "end_date": "2024-01-05"})
        periods = coordinator.get_periods()
        assert periods[0]["start_date"] == "2024-01-01"
        assert periods[1]["start_date"] == "2024-02-01"

    def test_get_cycle_length(self, coordinator):
        """Test getting cycle length."""
        coordinator._data = {"cycle_length": 30}
        assert coordinator.get_cycle_length() == 30

    def test_get_period_length(self, coordinator):
        """Test getting period length."""
        coordinator._data = {"period_length": 6}
        assert coordinator.get_period_length() == 6

    def test_get_last_period_start(self, coordinator):
        """Test getting last period start."""
        coordinator._data = {"last_period_start": "2024-01-01"}
        assert coordinator.get_last_period_start() == "2024-01-01"

    def test_calculate_cycle_day(self, coordinator):
        """Test calculating cycle day."""
        coordinator._data = {
            "last_period_start": "2024-01-01",
            "cycle_length": 28,
        }
        # Same day = day 1
        assert coordinator.calculate_cycle_day("2024-01-01") == 1
        # Next day = day 2
        assert coordinator.calculate_cycle_day("2024-01-02") == 2
        # After 28 days = day 1 again
        assert coordinator.calculate_cycle_day("2024-01-29") == 1

    def test_calculate_cycle_day_no_last_period(self, coordinator):
        """Test calculating cycle day with no last period."""
        coordinator._data = {"last_period_start": None, "cycle_length": 28}
        assert coordinator.calculate_cycle_day("2024-01-01") == 1

    def test_calculate_phase(self, coordinator):
        """Test calculating cycle phase."""
        coordinator._data = {
            "last_period_start": "2024-01-01",
            "cycle_length": 28,
            "period_length": 5,
        }
        # Day 1-5 = menstrual
        assert coordinator.calculate_phase("2024-01-01") == "menstrual"
        assert coordinator.calculate_phase("2024-01-05") == "menstrual"
        # Day 6-12 = follicular (cycle_length // 2 - 1 = 13, so day < 13)
        assert coordinator.calculate_phase("2024-01-06") == "follicular"
        assert coordinator.calculate_phase("2024-01-12") == "follicular"
        # Day 13-15 = ovulatory (cycle_length // 2 + 1 = 15, so day <= 15)
        assert coordinator.calculate_phase("2024-01-13") == "ovulatory"
        assert coordinator.calculate_phase("2024-01-15") == "ovulatory"
        # Day 16+ = luteal
        assert coordinator.calculate_phase("2024-01-16") == "luteal"
        assert coordinator.calculate_phase("2024-01-28") == "luteal"

    def test_predict_next_period(self, coordinator):
        """Test predicting next period."""
        coordinator._data = {
            "last_period_start": "2024-01-01",
            "cycle_length": 28,
        }
        next_period = coordinator.predict_next_period("2024-01-15")
        assert next_period == "2024-01-29"

    def test_predict_next_period_uses_history(self, coordinator):
        """Test predicting next period uses history when available."""
        coordinator._data = {
            "periods": [
                {"start_date": "2024-01-01", "end_date": "2024-01-05"},
                {"start_date": "2024-01-29", "end_date": "2024-02-02"},
                {"start_date": "2024-02-26", "end_date": "2024-03-01"},
            ],
            "last_period_start": "2024-02-26",
            "cycle_length": 28,
            "prediction_algorithm": "arithmetic_mean",
        }
        # Cycle lengths from history: 28, 28 -> mean = 28
        # Last period start: 2024-02-26 + 28 days = 2024-03-25
        next_period = coordinator.predict_next_period("2024-03-15")
        assert next_period == "2024-03-25"

    def test_predict_next_period_no_last_period(self, coordinator):
        """Test predicting next period with no last period."""
        coordinator._data = {
            "last_period_start": None,
            "cycle_length": 28,
        }
        next_period = coordinator.predict_next_period("2024-01-15")
        assert next_period == "2024-02-12"

    def test_get_next_ovulation_date(self, coordinator):
        """Test getting next ovulation date."""
        coordinator._data = {
            "last_period_start": "2024-01-01",
            "cycle_length": 28,
        }
        ovulation_date = coordinator.get_next_ovulation_date()
        assert ovulation_date is not None
        # Should be a valid ISO date string
        parsed = date.fromisoformat(ovulation_date)
        assert isinstance(parsed, date)
        # Should be on or after today
        assert parsed >= date.today()

    def test_get_next_ovulation_date_no_last_period(self, coordinator):
        """Test getting next ovulation date with no last period."""
        coordinator._data = {
            "last_period_start": None,
            "cycle_length": 28,
        }
        assert coordinator.get_next_ovulation_date() is None

    def test_get_statistics_insufficient_data(self, coordinator):
        """Test statistics with insufficient data."""
        coordinator._data = {
            "periods": [{"start_date": "2024-01-01", "end_date": "2024-01-05"}],
            "cycle_length": 28,
            "period_length": 5,
        }
        stats = coordinator.get_statistics()
        assert stats["average_cycle_length"] == 28
        assert stats["average_period_length"] == 5
        assert stats["cycle_length_std_dev"] == 0.0
        assert stats["total_cycles_tracked"] == 1

    def test_get_statistics_with_data(self, coordinator):
        """Test statistics with sufficient data."""
        coordinator._data = {
            "periods": [
                {"start_date": "2024-01-01", "end_date": "2024-01-05"},
                {"start_date": "2024-01-29", "end_date": "2024-02-02"},
                {"start_date": "2024-02-26", "end_date": "2024-03-01"},
            ],
            "cycle_length": 28,
            "period_length": 5,
        }
        stats = coordinator.get_statistics()
        # Cycle lengths: 28, 28 (from 2024-01-01 to 2024-01-29 = 28 days, 2024-01-29 to 2024-02-26 = 28 days)
        assert stats["total_cycles_tracked"] == 2
        assert stats["average_cycle_length"] == 28.0
        assert stats["average_period_length"] == 5.0
        assert stats["shortest_cycle"] == 28
        assert stats["longest_cycle"] == 28
