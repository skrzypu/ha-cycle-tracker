"""Data update coordinator for Cycle Tracker."""

import logging
from datetime import date, timedelta
from typing import Any, TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CYCLE_LENGTH,
    CONF_LAST_PERIOD_START,
    CONF_PERIOD_LENGTH,
    CONF_PREDICTION_ALGORITHM,
    DEFAULT_CYCLE_LENGTH,
    DEFAULT_PERIOD_LENGTH,
    DEFAULT_PREDICTION_ALGORITHM,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .domain.models import Period, legacy_period_id
from .domain.ports import Clock, PredictionConfig
from .domain.prediction import Snapshot, build_snapshot

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")


class HomeAssistantClock:
    """Clock port backed by Home Assistant's local time."""

    def today(self) -> date:
        """Return the current local date."""
        return dt_util.now().date()


class CycleTrackerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Adapter between Home Assistant storage and the pure prediction domain."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator.

        The entry is passed explicitly instead of letting the base class read
        the ContextVar: the coordinator relies on ``async_config_entry_first_refresh``,
        which only works with an entry, and a reload triggered by an options
        change runs without the setup ContextVar.
        """
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_UPDATE_INTERVAL_HOURS),
        )
        self.entry = entry
        self.store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {}
        self._clock: Clock = HomeAssistantClock()
        self._snapshot: Snapshot | None = None

    def _setting(self, key: str, default: _T) -> _T:
        """Resolve one setting: entry options, then setup data, then the default.

        The config entry owns the settings; storage keeps recorded periods only,
        so a setting copied into older stored data can never win.
        """
        return self.entry.options.get(key, self.entry.data.get(key, default))

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from storage."""
        try:
            data = await self.store.async_load()
        except Exception as err:
            raise UpdateFailed(f"Error loading data: {err}") from err

        self._data = self._normalize_data(data)
        self._invalidate_snapshot()
        return self._data

    def _get_default_data(self) -> dict[str, Any]:
        """Get default data structure."""
        return {"periods": []}

    def _normalize_data(self, data: object) -> dict[str, Any]:
        """Keep the recorded periods and drop any stored settings copy."""
        if data is None:
            return self._get_default_data()
        if not isinstance(data, dict):
            _LOGGER.warning("Ignoring malformed stored data: %s", data)
            return self._get_default_data()

        periods = data.get("periods")
        if periods is None:
            return self._get_default_data()
        if not isinstance(periods, list):
            _LOGGER.warning("Ignoring malformed stored periods: %s", periods)
            return self._get_default_data()
        return {"periods": periods}

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
        self._invalidate_snapshot()

    def get_domain_periods(self) -> list[Period]:
        """Adapt the stored period rows to domain periods.

        Stored rows keep the legacy ``{start_date, end_date, flow_intensity}``
        shape; identity is derived from the start date until the logging use
        case persists a ``period_id``.
        """
        periods = [
            period
            for row in self.get_periods()
            if (period := self._adapt_period(row)) is not None
        ]
        periods.sort(key=lambda period: period.start)
        return periods

    @staticmethod
    def _adapt_period(row: dict[str, Any]) -> Period | None:
        """Adapt one stored row, warning instead of failing on malformed data."""
        raw_start = row.get("start_date")
        if not isinstance(raw_start, str):
            _LOGGER.warning("Ignoring stored period without a start date: %s", row)
            return None
        try:
            start = date.fromisoformat(raw_start)
        except ValueError:
            _LOGGER.warning("Ignoring stored period with an invalid start: %s", row)
            return None

        raw_end = row.get("end_date")
        end: date | None = None
        if raw_end is not None:
            try:
                end = date.fromisoformat(raw_end)
            except (TypeError, ValueError):
                _LOGGER.warning("Ignoring stored period with an invalid end: %s", row)
                return None
            if end < start:
                _LOGGER.warning(
                    "Ignoring stored period ending before its start: %s", row
                )
                return None
            if end == start:
                # The logging contract stores ``end_date == start_date`` for a
                # period that has not ended yet, so an equal end marks it open.
                # A genuine one-day period is indistinguishable until logging
                # persists an explicit open flag.
                end = None

        return Period(
            id=legacy_period_id(start),
            start=start,
            end=end,
            flow=row.get("flow_intensity"),
        )

    def get_prediction_config(self) -> PredictionConfig:
        """Build the domain configuration from the config entry settings."""
        return PredictionConfig(
            period_length=self.get_period_length(),
            cycle_length=self.get_cycle_length(),
        )

    @property
    def snapshot(self) -> Snapshot:
        """Return the derived snapshot, cached for the current local date."""
        reference_date = self._clock.today()
        if self._snapshot is None or self._snapshot.reference_date != reference_date:
            self._snapshot = build_snapshot(
                self.get_domain_periods(),
                self.get_prediction_config(),
                self.get_prediction_algorithm(),
                reference_date,
            )
        return self._snapshot

    def _invalidate_snapshot(self) -> None:
        """Drop the cached snapshot after the underlying data changed."""
        self._snapshot = None

    @callback
    def async_set_updated_data(self, data: dict[str, Any]) -> None:
        """Publish new data and rebuild the snapshot on the next read."""
        self._invalidate_snapshot()
        super().async_set_updated_data(data)

    def get_cycle_length(self) -> int:
        """Get cycle length."""
        return self._setting(CONF_CYCLE_LENGTH, DEFAULT_CYCLE_LENGTH)

    def get_period_length(self) -> int:
        """Get period length."""
        return self._setting(CONF_PERIOD_LENGTH, DEFAULT_PERIOD_LENGTH)

    def get_last_period_start(self) -> str | None:
        """Get the most recent period start date."""
        periods = self.get_periods()
        if periods:
            return periods[-1]["start_date"]
        fallback: str | None = None
        return self._setting(CONF_LAST_PERIOD_START, fallback)

    def get_prediction_algorithm(self) -> str:
        """Get prediction algorithm."""
        return self._setting(CONF_PREDICTION_ALGORITHM, DEFAULT_PREDICTION_ALGORITHM)
