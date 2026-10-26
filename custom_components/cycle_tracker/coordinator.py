"""Data update coordinator for Cycle Tracker."""

from datetime import date, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    STORAGE_KEY,
    STORAGE_VERSION,
    CONF_CYCLE_LENGTH,
    CONF_PERIOD_LENGTH,
    CONF_LAST_PERIOD_START,
    CONF_PREDICTION_ALGORITHM,
    CONF_NOTIFICATION_OFFSET_DAYS,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_NOTIFICATION_TIME,
    DEFAULT_CYCLE_LENGTH,
    DEFAULT_PERIOD_LENGTH,
    DEFAULT_PREDICTION_ALGORITHM,
    DEFAULT_NOTIFICATION_OFFSET_DAYS,
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_NOTIFICATION_TIME,
)
from .prediction import get_algorithm

_LOGGER = logging.getLogger(__name__)


class CycleTrackerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching cycle data."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_UPDATE_INTERVAL_HOURS),
        )
        self.entry = entry
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from storage."""
        try:
            data = await self.store.async_load()
            if data is None:
                data = self._get_default_data()
            self._data = data
            return data
        except Exception as err:
            raise UpdateFailed(f"Error loading data: {err}") from err

    def _get_default_data(self) -> dict[str, Any]:
        """Get default data structure."""
        return {
            "periods": [],
            "cycle_length": self.entry.data.get(
                CONF_CYCLE_LENGTH, DEFAULT_CYCLE_LENGTH
            ),
            "period_length": self.entry.data.get(
                CONF_PERIOD_LENGTH, DEFAULT_PERIOD_LENGTH
            ),
            "last_period_start": self.entry.data.get(CONF_LAST_PERIOD_START),
            "prediction_algorithm": self.entry.data.get(
                CONF_PREDICTION_ALGORITHM, DEFAULT_PREDICTION_ALGORITHM
            ),
            "notification_offset_days": self.entry.data.get(
                CONF_NOTIFICATION_OFFSET_DAYS, DEFAULT_NOTIFICATION_OFFSET_DAYS
            ),
            "enable_notifications": self.entry.data.get(
                CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS
            ),
            "notification_time": self.entry.data.get(
                CONF_NOTIFICATION_TIME, DEFAULT_NOTIFICATION_TIME
            ),
        }

    async def async_save_data(self) -> None:
        """Save data to storage."""
        await self.store.async_save(self._data)

    def get_periods(self) -> list[dict[str, Any]]:
        """Get list of periods."""
        return self._data.get("periods", [])

    def add_period(self, period: dict[str, Any]) -> None:
        """Add a period."""
        periods = self.get_periods()
        periods.append(period)
        periods.sort(key=lambda p: p["start_date"])
        self._data["periods"] = periods

    def get_cycle_length(self) -> int:
        """Get cycle length."""
        return self._data.get("cycle_length", DEFAULT_CYCLE_LENGTH)

    def get_period_length(self) -> int:
        """Get period length."""
        return self._data.get("period_length", DEFAULT_PERIOD_LENGTH)

    def get_last_period_start(self) -> str | None:
        """Get last period start date."""
        return self._data.get("last_period_start")

    def get_prediction_algorithm(self) -> str:
        """Get prediction algorithm."""
        return self._data.get("prediction_algorithm", DEFAULT_PREDICTION_ALGORITHM)

    def _get_cycle_lengths_from_history(self) -> list[int]:
        """Derive cycle lengths from consecutive period start dates (oldest to newest)."""
        periods = self.get_periods()
        if len(periods) < 2:
            return []
        cycle_lengths: list[int] = []
        for i in range(1, len(periods)):
            prev_start = date.fromisoformat(periods[i - 1]["start_date"])
            curr_start = date.fromisoformat(periods[i]["start_date"])
            cycle_lengths.append((curr_start - prev_start).days)
        return cycle_lengths

    def calculate_cycle_day(self, reference_date: str) -> int:
        """Calculate current cycle day."""
        last_start = self.get_last_period_start()
        if not last_start:
            return 1
        from datetime import date

        last = date.fromisoformat(last_start)
        ref = date.fromisoformat(reference_date)
        delta = (ref - last).days
        cycle_length = self.get_cycle_length()
        return (delta % cycle_length) + 1

    def calculate_phase(self, reference_date: str) -> str:
        """Calculate current cycle phase."""
        cycle_day = self.calculate_cycle_day(reference_date)
        period_length = self.get_period_length()
        cycle_length = self.get_cycle_length()

        if cycle_day <= period_length:
            return "menstrual"
        elif cycle_day < (cycle_length // 2 - 1):
            return "follicular"
        elif cycle_day <= (cycle_length // 2 + 1):
            return "ovulatory"
        else:
            return "luteal"

    def predict_next_period(self, reference_date: str) -> str:
        """Predict next period start date using history if available."""
        from datetime import date, timedelta

        last_start = self.get_last_period_start()
        if not last_start:
            ref = date.fromisoformat(reference_date)
            return (ref + timedelta(days=self.get_cycle_length())).isoformat()

        last = date.fromisoformat(last_start)
        cycle_lengths = self._get_cycle_lengths_from_history()
        if len(cycle_lengths) >= 2:
            # Use most recent up to 6 cycle lengths
            recent_lengths = cycle_lengths[-6:]
            algorithm = get_algorithm(self.get_prediction_algorithm())
            predicted_length = algorithm(recent_lengths)
            return (last + timedelta(days=predicted_length)).isoformat()

        cycle_length = self.get_cycle_length()
        return (last + timedelta(days=cycle_length)).isoformat()

    def get_next_ovulation_date(self) -> str | None:
        """Get next predicted ovulation date as ISO string."""
        from datetime import date, timedelta

        last_start = self.get_last_period_start()
        if not last_start:
            return None
        last = date.fromisoformat(last_start)
        cycle_length = self.get_cycle_length()
        ovulation_offset = cycle_length // 2
        next_ovulation = last + timedelta(days=ovulation_offset)
        today = date.today()
        while next_ovulation < today:
            next_ovulation += timedelta(days=cycle_length)
        return next_ovulation.isoformat()

    def get_statistics(self) -> dict[str, Any]:
        """Get cycle statistics."""
        periods = self.get_periods()
        if len(periods) < 2:
            return {
                "average_cycle_length": self.get_cycle_length(),
                "average_period_length": self.get_period_length(),
                "cycle_length_std_dev": 0.0,
                "period_length_std_dev": 0.0,
                "total_cycles_tracked": len(periods),
                "shortest_cycle": self.get_cycle_length(),
                "longest_cycle": self.get_cycle_length(),
            }

        cycle_lengths = []
        period_lengths = []
        for i in range(1, len(periods)):
            prev_start = date.fromisoformat(periods[i - 1]["start_date"])
            curr_start = date.fromisoformat(periods[i]["start_date"])
            cycle_lengths.append((curr_start - prev_start).days)
            prev_period_start = date.fromisoformat(periods[i - 1]["start_date"])
            prev_period_end = date.fromisoformat(periods[i - 1]["end_date"])
            period_lengths.append((prev_period_end - prev_period_start).days + 1)

        import statistics

        avg_cycle = (
            statistics.mean(cycle_lengths) if cycle_lengths else self.get_cycle_length()
        )
        avg_period = (
            statistics.mean(period_lengths)
            if period_lengths
            else self.get_period_length()
        )
        std_cycle = statistics.stdev(cycle_lengths) if len(cycle_lengths) > 1 else 0.0
        std_period = (
            statistics.stdev(period_lengths) if len(period_lengths) > 1 else 0.0
        )

        return {
            "average_cycle_length": round(avg_cycle, 1),
            "average_period_length": round(avg_period, 1),
            "cycle_length_std_dev": round(std_cycle, 1),
            "period_length_std_dev": round(std_period, 1),
            "total_cycles_tracked": len(cycle_lengths),
            "shortest_cycle": min(cycle_lengths)
            if cycle_lengths
            else self.get_cycle_length(),
            "longest_cycle": max(cycle_lengths)
            if cycle_lengths
            else self.get_cycle_length(),
        }
