import pytest
from unittest.mock import MagicMock, AsyncMock


class MockConfigEntry:
    """Simple mock config entry for unit tests."""

    def __init__(self, domain, data, options=None, entry_id="test_entry_id"):
        self.domain = domain
        self.data = data
        self.options = options or {}
        self.entry_id = entry_id


@pytest.fixture
def mock_config_entry():
    return MockConfigEntry(
        domain="cycle_tracker",
        data={
            "cycle_length": 28,
            "period_length": 5,
            "last_period_start": "2024-01-01",
            "prediction_algorithm": "weighted_moving_average",
            "notification_offset_days": 2,
            "enable_notifications": False,
            "notification_time": "08:00",
        },
        options={},
    )


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    hass.services.async_remove = MagicMock()
    return hass


@pytest.fixture
def mock_store():
    """Create a mock store."""
    store = AsyncMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    return store
