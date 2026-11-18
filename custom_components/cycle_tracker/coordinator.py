"""Data update coordinator for Cycle Tracker."""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, TypeVar
from uuid import uuid4

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .config_flow import _resolve_service_account_path
from .const import (
    CONF_CYCLE_LENGTH,
    CONF_LAST_PERIOD_START,
    CONF_PERIOD_LENGTH,
    CONF_POLL_INTERVAL,
    CONF_PREDICTION_ALGORITHM,
    CONF_SERVICE_ACCOUNT_FILE,
    CONF_SPREADSHEET_ID,
    CONF_WORKSHEET,
    DEFAULT_CYCLE_LENGTH,
    DEFAULT_PERIOD_LENGTH,
    DEFAULT_POLL_INTERVAL_MINUTES,
    DEFAULT_PREDICTION_ALGORITHM,
    DOMAIN,
    MAX_POLL_INTERVAL_MINUTES,
    MIN_POLL_INTERVAL_MINUTES,
    STORAGE_KEY_SYNC_CACHE,
    STORAGE_VERSION_SYNC_CACHE,
)
from .domain.models import Period
from .domain.ports import Clock, PeriodRepository, PredictionConfig
from .domain.prediction import Snapshot, build_snapshot
from .repairs import (
    ISSUE_SHEET_AUTH_FAILED,
    ISSUE_SHEET_NOT_CONFIGURED,
    ISSUE_SHEET_ROWS_INVALID,
    ISSUE_SHEET_SCHEMA_INVALID,
    ISSUE_SHEET_UNREACHABLE,
    async_create_sheet_issue,
    async_delete_sheet_issue,
    classify_sheet_exception,
)
from .repository import (
    SheetsPeriodRepository,
    _deserialize_period,
    _serialize_period,
)
from .sheets import ServiceAccountAccessTokenError, SheetsApiError, SheetsClient

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")


class HomeAssistantClock:
    """Clock port backed by Home Assistant's local time."""

    def today(self) -> date:
        """Return the current local date."""
        return dt_util.now().date()


class CycleTrackerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Adapter between Home Assistant storage and the pure prediction domain."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        repo: PeriodRepository | None = None,
        cache_store: Store[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize the coordinator.

        The entry is passed explicitly instead of letting the base class read
        the ContextVar: the coordinator relies on ``async_config_entry_first_refresh``,
        which only works with an entry, and a reload triggered by an options
        change runs without the setup ContextVar.

        ``repo`` and ``cache_store`` are exposed for tests so the coordinator
        can be driven with a fake repository and an in-memory Store.
        """
        self.entry = entry
        self._repo: PeriodRepository | None = (
            repo if repo is not None else self._build_repository(hass, entry)
        )
        self._is_remote = isinstance(self._repo, SheetsPeriodRepository)
        self._cache_store: Store[dict[str, Any]] | None = (
            cache_store
            if cache_store is not None
            else (
                Store(hass, STORAGE_VERSION_SYNC_CACHE, STORAGE_KEY_SYNC_CACHE)
                if self._is_remote
                else None
            )
        )
        poll_minutes = self._poll_interval_minutes()
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=poll_minutes),
        )
        self._data: dict[str, Any] = {}
        self._periods: list[Period] = []
        self._clock: Clock = HomeAssistantClock()
        self._snapshot: Snapshot | None = None
        self._consecutive_failures = 0
        self._last_sync: datetime | None = None
        self._last_error: str | None = None
        self._not_configured_issue_created = False

    @staticmethod
    def _build_repository(
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> PeriodRepository | None:
        """Build the configured repository when sheet settings are present."""
        data = entry.data
        spreadsheet_id = data.get(CONF_SPREADSHEET_ID)
        worksheet = data.get(CONF_WORKSHEET)
        service_account_file = data.get(CONF_SERVICE_ACCOUNT_FILE)
        if spreadsheet_id and worksheet and service_account_file:
            path = _resolve_service_account_path(hass, service_account_file)
            if path is None:
                _LOGGER.error(
                    "Service account key path escapes the config directory: %s",
                    service_account_file,
                )
                return None
            with open(path, encoding="utf-8") as fp:
                service_account_info = json.load(fp)
            client = SheetsClient(hass, service_account_info)
            return SheetsPeriodRepository(client, spreadsheet_id, worksheet)
        return None

    def _poll_interval_minutes(self) -> int:
        """Return the configured poll interval clamped to the supported range."""
        if self._repo is None:
            return DEFAULT_POLL_INTERVAL_MINUTES
        try:
            value = int(
                self.entry.options.get(
                    CONF_POLL_INTERVAL,
                    self.entry.data.get(
                        CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL_MINUTES
                    ),
                )
            )
        except (TypeError, ValueError):
            value = DEFAULT_POLL_INTERVAL_MINUTES
        return max(MIN_POLL_INTERVAL_MINUTES, min(MAX_POLL_INTERVAL_MINUTES, value))

    def _setting(self, key: str, default: _T) -> _T:
        """Resolve one setting: entry options, then setup data, then the default.

        The config entry owns the settings; storage keeps recorded periods only,
        so a setting copied into older stored data can never win.
        """
        return self.entry.options.get(key, self.entry.data.get(key, default))

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from storage via the repository port.

        For remote repositories this is a read-through cache: a successful read
        snapshots the data locally, while repeated failures fall back to the
        cached snapshot and eventually mark the coordinator unavailable.
        """
        if self._repo is None:
            if not self._not_configured_issue_created:
                async_create_sheet_issue(self.hass, ISSUE_SHEET_NOT_CONFIGURED)
                self._not_configured_issue_created = True
            self._data = {"periods": []}
            self._periods = []
            self._invalidate_snapshot()
            return self._data

        if self._cache_store is None:
            try:
                self._periods = await self._repo.read_all()
            except Exception as err:
                raise UpdateFailed(f"Error loading data: {err}") from err

            self._data = {
                "periods": [_serialize_period(period) for period in self._periods]
            }
            self._invalidate_snapshot()
            return self._data

        try:
            self._periods = await self._repo.read_all()
        except Exception as err:
            self._consecutive_failures += 1
            self._last_error = str(err)
            self._sync_repair_issues(err)
            cached = await self._cache_store.async_load()
            if not isinstance(cached, dict):
                raise UpdateFailed(f"Error loading data: {err}") from err

            self._periods = [
                period
                for row in cached.get("periods", [])
                if isinstance(row, dict)
                and (period := _deserialize_period(row)) is not None
            ]
            self._data = {
                "periods": [_serialize_period(period) for period in self._periods]
            }
            self._invalidate_snapshot()
            await self._persist_cache_state()
            return self._data

        self._consecutive_failures = 0
        self._last_error = None
        self._last_sync = dt_util.utcnow()
        self._data = {
            "periods": [_serialize_period(period) for period in self._periods]
        }
        self._invalidate_snapshot()
        self._sync_repair_issues(None)
        await self._persist_cache_state()
        return self._data

    def _sync_repair_issues(self, exc: Exception | None) -> None:
        """Create or clear sheet repair issues after a refresh attempt."""
        if exc is None:
            async_delete_sheet_issue(self.hass, ISSUE_SHEET_NOT_CONFIGURED)
            async_delete_sheet_issue(self.hass, ISSUE_SHEET_AUTH_FAILED)
            async_delete_sheet_issue(self.hass, ISSUE_SHEET_UNREACHABLE)
            async_delete_sheet_issue(self.hass, ISSUE_SHEET_SCHEMA_INVALID)
            if (
                isinstance(self._repo, SheetsPeriodRepository)
                and self._repo.last_invalid_reports
            ):
                async_create_sheet_issue(
                    self.hass,
                    ISSUE_SHEET_ROWS_INVALID,
                    {
                        "count": str(len(self._repo.last_invalid_reports)),
                    },
                )
            else:
                async_delete_sheet_issue(self.hass, ISSUE_SHEET_ROWS_INVALID)
            return

        issue_id = classify_sheet_exception(exc)
        async_delete_sheet_issue(self.hass, ISSUE_SHEET_ROWS_INVALID)
        if issue_id in {
            ISSUE_SHEET_AUTH_FAILED,
            ISSUE_SHEET_UNREACHABLE,
            ISSUE_SHEET_SCHEMA_INVALID,
        }:
            async_create_sheet_issue(self.hass, issue_id)

    async def _persist_cache_state(self) -> None:
        """Write the current cache metadata and snapshot to local storage."""
        assert self._cache_store is not None
        await self._cache_store.async_save(
            {
                "periods": self._data.get("periods", []),
                "last_sync": self._last_sync.isoformat() if self._last_sync else None,
                "last_error": self._last_error,
                "consecutive_failures": self._consecutive_failures,
            }
        )

    async def async_save_data(self) -> None:
        """Persist the in-memory periods to storage."""
        if self._repo is None:
            return
        for period in self._periods:
            await self._repo.upsert(period)
        self._periods = await self._repo.read_all()
        self._data = {
            "periods": [_serialize_period(period) for period in self._periods]
        }

    def get_periods(self) -> list[dict[str, Any]]:
        """Get list of serialized period rows."""
        return list(self._data.get("periods", []))

    def add_period(self, row: dict[str, Any]) -> None:
        """Add a period from a serialized row."""
        period = _deserialize_period(row)
        if period is None:
            return
        self._periods.append(period)
        self._periods.sort(key=lambda period: period.start)
        self._data = {
            "periods": [_serialize_period(period) for period in self._periods]
        }
        self._invalidate_snapshot()

    def get_domain_periods(self) -> list[Period]:
        """Return the stored domain periods, already sorted by start date."""
        return list(self._periods)

    async def async_log_start(self, start: date, flow: str) -> None:
        """Log the start of a period through the repository.

        If the latest stored period already starts on ``start``, its flow is
        updated and it stays open; otherwise a new open period is created.
        """
        if self._repo is None:
            raise HomeAssistantError(
                "Cycle Tracker is not configured with a Google Sheet. "
                "Complete the sheet configuration step before logging periods."
            )

        now = dt_util.utcnow()

        if self._periods and self._periods[-1].start == start:
            latest = self._periods[-1]
            period = Period(
                id=latest.id,
                start=latest.start,
                end=None,
                flow=flow,
                notes=latest.notes,
                updated_at=now,
            )
        else:
            period = Period(
                id=uuid4(),
                start=start,
                end=None,
                flow=flow,
                updated_at=now,
            )

        try:
            await self._repo.upsert(period)
        except (ServiceAccountAccessTokenError, SheetsApiError) as err:
            raise HomeAssistantError(
                f"Cycle Tracker could not write to the Google Sheet: {err}"
            ) from err
        except aiohttp.ClientError as err:
            raise HomeAssistantError(
                f"Cycle Tracker could not reach the Google Sheet: {err}"
            ) from err
        self._upsert_in_memory(period)
        self._invalidate_snapshot()

    async def async_log_end(self, end: date) -> dict[str, Any]:
        """Log the end of the latest open period through the repository.

        Returns the same response shape the service layer exposes to callers.
        """
        if self._repo is None:
            raise HomeAssistantError(
                "Cycle Tracker is not configured with a Google Sheet. "
                "Complete the sheet configuration step before logging periods."
            )

        if not self._periods:
            return {"success": False, "message": "No period started to end"}

        latest = self._periods[-1]
        if latest.end is not None:
            return {"success": False, "message": "Period already ended"}

        end_str = end.isoformat()
        start_str = latest.start.isoformat()
        if end < latest.start:
            return {
                "success": False,
                "message": (
                    f"End date {end_str} precedes the period start {start_str}"
                ),
            }

        period = Period(
            id=latest.id,
            start=latest.start,
            end=end,
            flow=latest.flow,
            notes=latest.notes,
            updated_at=dt_util.utcnow(),
        )
        try:
            await self._repo.upsert(period)
        except (ServiceAccountAccessTokenError, SheetsApiError) as err:
            raise HomeAssistantError(
                f"Cycle Tracker could not write to the Google Sheet: {err}"
            ) from err
        except aiohttp.ClientError as err:
            raise HomeAssistantError(
                f"Cycle Tracker could not reach the Google Sheet: {err}"
            ) from err
        self._upsert_in_memory(period)
        self._invalidate_snapshot()
        return {"success": True, "message": f"Period end logged for {end_str}"}

    def _upsert_in_memory(self, period: Period) -> None:
        """Replace or append a period in the cached lists."""
        for index, existing in enumerate(self._periods):
            if existing.id == period.id:
                self._periods[index] = period
                break
        else:
            self._periods.append(period)
        self._periods.sort(key=lambda period: period.start)
        self._data = {
            "periods": [_serialize_period(period) for period in self._periods]
        }

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

    @property
    def available(self) -> bool:
        """Return False when the sheet is not configured or after three failures."""
        if self._repo is None:
            return False
        if self._cache_store is None:
            return self.last_update_success
        return self._consecutive_failures < 3

    @property
    def last_sync(self) -> datetime | None:
        """Return the timestamp of the last successful remote read."""
        return self._last_sync

    @property
    def last_error(self) -> str | None:
        """Return the message from the most recent remote read failure."""
        return self._last_error

    @property
    def consecutive_failures(self) -> int:
        """Return the current streak of consecutive remote read failures."""
        return self._consecutive_failures

    @property
    def sync_status(self) -> dict[str, Any]:
        """Return a dict that sensors can expose as attributes."""
        return {
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "last_error": self._last_error,
            "consecutive_failures": self._consecutive_failures,
        }

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
