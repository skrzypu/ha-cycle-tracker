"""Config flow for Cycle Tracker."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, TypeVar

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CYCLE_LENGTH,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_IMPORT_CACHED,
    CONF_LAST_PERIOD_START,
    CONF_NOTIFICATION_OFFSET_DAYS,
    CONF_NOTIFICATION_TIME,
    CONF_PERIOD_LENGTH,
    CONF_POLL_INTERVAL,
    CONF_PREDICTION_ALGORITHM,
    CONF_SERVICE_ACCOUNT_FILE,
    CONF_SPREADSHEET_ID,
    CONF_WORKSHEET,
    DEFAULT_CYCLE_LENGTH,
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_NOTIFICATION_OFFSET_DAYS,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_PERIOD_LENGTH,
    DEFAULT_POLL_INTERVAL_MINUTES,
    DEFAULT_PREDICTION_ALGORITHM,
    DOMAIN,
    MAX_POLL_INTERVAL_MINUTES,
    MIN_POLL_INTERVAL_MINUTES,
    PREDICTION_ALGORITHMS,
)
from .repository import (
    SheetSchemaError,
    SheetsPeriodRepository,
    _header_indices,
    import_cached_periods,
)
from .sheets import ServiceAccountAccessTokenError, SheetsApiError, SheetsClient

_T = TypeVar("_T")

_LOGGER = logging.getLogger(__name__)


class _SheetValidationResult:
    """Outcome of validating a sheet during the config flow."""

    def __init__(
        self,
        error: str | None = None,
        data_rows: int = 0,
        client_email: str | None = None,
    ) -> None:
        self.error = error
        self.data_rows = data_rows
        self.client_email = client_email


def _load_service_account_key(path: Path) -> dict[str, Any]:
    """Load and parse a service-account JSON key file (sync)."""
    with open(path, encoding="utf-8") as fp:
        return json.load(fp)


def _setting(entry: ConfigEntry, key: str, default: _T) -> _T:
    """Resolve one setting: entry options, then setup data, then the default."""
    return entry.options.get(key, entry.data.get(key, default))


def _resolve_service_account_path(hass: Any, path_str: str) -> Path | None:
    """Resolve a key path inside ``hass.config.config_dir``.

    Relative paths are resolved against the config directory. Absolute paths
    are accepted only when they lie inside it. Returns ``None`` for a path
    that escapes the config directory or does not exist.
    """
    config_dir = Path(hass.config.config_dir).resolve()
    path = Path(path_str)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (config_dir / path).resolve()

    try:
        resolved.relative_to(config_dir)
    except ValueError:
        return None

    return resolved


def _sheet_api_error_key(exc: SheetsApiError) -> str:
    """Map a Sheets API error to one of the five sheet step error keys."""
    body: dict[str, Any] = exc.args[0] if exc.args else {}
    status = body.get("error", {}).get("code", 0)
    if status in (401, 403):
        return "invalid_auth"
    if status == 404:
        return "sheet_not_found"
    if status == 400:
        return "invalid_range"
    return "cannot_connect"


_SHEET_ID_RE = re.compile(r"[A-Za-z0-9_-]{20,}")
_SHEET_URL_RE = re.compile(r"/spreadsheets/d/([A-Za-z0-9_-]+)")
_SHEET_QUERY_ID_RE = re.compile(r"[?&]id=([A-Za-z0-9_-]+)")


def _normalize_spreadsheet_id(raw: str) -> str | None:
    """Return a bare spreadsheet ID from an ID or a pasted Google Sheets URL."""
    value = str(raw).strip()
    match = _SHEET_URL_RE.search(value) or _SHEET_QUERY_ID_RE.search(value)
    if match is not None:
        value = match.group(1)
    if not _SHEET_ID_RE.fullmatch(value):
        return None
    return value


def _clamp_poll_interval(value: int) -> int:
    """Clamp the poll interval to the supported 1–60 minute range."""
    return max(MIN_POLL_INTERVAL_MINUTES, min(MAX_POLL_INTERVAL_MINUTES, int(value)))


async def _async_validate_sheet(
    hass: Any,
    spreadsheet_id: str,
    worksheet: str,
    service_account_file: str,
) -> _SheetValidationResult:
    """Check the key file, auth, sheet presence and header schema."""
    spreadsheet_id = str(spreadsheet_id).strip()
    worksheet = str(worksheet).strip()
    service_account_file = str(service_account_file).strip()

    path = _resolve_service_account_path(hass, service_account_file)
    if path is None:
        _LOGGER.warning(
            "Cycle Tracker: service account key path %r does not resolve inside"
            " %s; rejecting the sheet configuration",
            service_account_file,
            hass.config.config_dir,
        )
        return _SheetValidationResult("cannot_connect")

    try:
        service_account_info = await hass.async_add_executor_job(
            _load_service_account_key, path
        )
    except (FileNotFoundError, PermissionError, OSError, json.JSONDecodeError) as exc:
        _LOGGER.warning(
            "Cycle Tracker: failed to load service account key %s: %s: %s",
            path,
            type(exc).__name__,
            exc,
        )
        return _SheetValidationResult("cannot_connect")

    client_email = service_account_info.get("client_email")

    try:
        client = SheetsClient(hass, service_account_info)
        rows = await client.read_rows(spreadsheet_id, worksheet)
    except ServiceAccountAccessTokenError as exc:
        body: dict[str, Any] = exc.args[0] if exc.args else {}
        _LOGGER.warning(
            "Cycle Tracker: service account token request failed: error=%s"
            " error_description=%s",
            body.get("error"),
            body.get("error_description"),
        )
        return _SheetValidationResult("invalid_auth", client_email=client_email)
    except SheetsApiError as exc:
        body = exc.args[0] if exc.args else {}
        error_body = body.get("error", {})
        _LOGGER.warning(
            "Cycle Tracker: Sheets API returned HTTP %s for spreadsheet %s"
            " worksheet %s: %s",
            error_body.get("code"),
            spreadsheet_id,
            worksheet,
            error_body.get("message"),
        )
        return _SheetValidationResult(
            _sheet_api_error_key(exc), client_email=client_email
        )
    except aiohttp.ClientError as exc:
        _LOGGER.warning(
            "Cycle Tracker: network error reading spreadsheet %s worksheet %s: %r",
            spreadsheet_id,
            worksheet,
            exc,
        )
        return _SheetValidationResult("cannot_connect", client_email=client_email)
    except TimeoutError:
        _LOGGER.warning(
            "Cycle Tracker: timed out reading spreadsheet %s worksheet %s",
            spreadsheet_id,
            worksheet,
        )
        return _SheetValidationResult("cannot_connect", client_email=client_email)

    if not rows:
        return _SheetValidationResult(None, data_rows=0, client_email=client_email)

    headers = rows[0]
    try:
        _header_indices(headers)
    except SheetSchemaError as exc:
        _LOGGER.warning(
            "Cycle Tracker: worksheet header is missing required columns."
            " spreadsheet=%s worksheet=%s headers=%s error=%s",
            spreadsheet_id,
            worksheet,
            headers,
            exc,
        )
        return _SheetValidationResult("invalid_schema", client_email=client_email)

    return _SheetValidationResult(
        None, data_rows=max(0, len(rows) - 1), client_email=client_email
    )


async def _async_local_cached_periods(hass: Any) -> list[Any]:
    """Return periods stored in the legacy local store, if any."""
    from .repository import LocalStoreRepository

    repo = LocalStoreRepository(hass)
    return await repo.read_all()


def _sheet_schema(
    hass: Any,
    defaults: dict[str, Any] | None = None,
    include_import: bool = False,
) -> vol.Schema:
    """Build the schema for the sheet step."""
    defaults = defaults or {}
    fields: dict[Any, Any] = {
        vol.Required(
            CONF_SPREADSHEET_ID,
            default=defaults.get(CONF_SPREADSHEET_ID, ""),
        ): str,
        vol.Required(
            CONF_WORKSHEET,
            default=defaults.get(CONF_WORKSHEET, "Sheet1"),
        ): str,
        vol.Required(
            CONF_SERVICE_ACCOUNT_FILE,
            default=defaults.get(CONF_SERVICE_ACCOUNT_FILE, ""),
        ): str,
        vol.Required(
            CONF_POLL_INTERVAL,
            default=defaults.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL_MINUTES),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=MIN_POLL_INTERVAL_MINUTES,
                max=MAX_POLL_INTERVAL_MINUTES,
                step=1,
                unit_of_measurement="minutes",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
    }
    if include_import:
        fields[
            vol.Optional(
                CONF_IMPORT_CACHED,
                default=False,
            )
        ] = selector.BooleanSelector()
    return vol.Schema(fields)


class CycleTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Cycle Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._sheet_input: dict[str, Any] | None = None
        self._sheet_account_email: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - basic configuration."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_preferences()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CYCLE_LENGTH,
                        default=DEFAULT_CYCLE_LENGTH,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=20,
                            max=45,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_PERIOD_LENGTH,
                        default=DEFAULT_PERIOD_LENGTH,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=2,
                            max=10,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_LAST_PERIOD_START,
                    ): selector.DateSelector(),
                }
            ),
            description_placeholders={
                "cycle_length_help": "Average length of your menstrual cycle in days (typically 21-35)",
                "period_length_help": "Average length of your period in days (typically 3-7)",
            },
        )

    async def async_step_preferences(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the preferences step."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_notifications()

        return self.async_show_form(
            step_id="preferences",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PREDICTION_ALGORITHM,
                        default=DEFAULT_PREDICTION_ALGORITHM,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=PREDICTION_ALGORITHMS,
                            translation_key="prediction_algorithm",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_NOTIFICATION_OFFSET_DAYS,
                        default=DEFAULT_NOTIFICATION_OFFSET_DAYS,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=14,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            description_placeholders={
                "algorithm_help": "Arithmetic Mean: simple average. Weighted Moving Average: recent cycles weighted more heavily.",
            },
        )

    async def async_step_notifications(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the notifications step."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_sheet()

        return self.async_show_form(
            step_id="notifications",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENABLE_NOTIFICATIONS,
                        default=DEFAULT_ENABLE_NOTIFICATIONS,
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_NOTIFICATION_TIME,
                        default=DEFAULT_NOTIFICATION_TIME,
                    ): selector.TimeSelector(),
                }
            ),
            description_placeholders={
                "notifications_help": "Enable notifications for period start, ovulation, and upcoming period reminders.",
            },
        )

    async def async_step_sheet(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the Google Sheets source-of-truth step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            raw_spreadsheet_id = str(user_input[CONF_SPREADSHEET_ID])
            spreadsheet_id = _normalize_spreadsheet_id(raw_spreadsheet_id)
            worksheet = str(user_input[CONF_WORKSHEET]).strip()
            service_account_file = str(user_input[CONF_SERVICE_ACCOUNT_FILE]).strip()
            if spreadsheet_id is None:
                _LOGGER.warning(
                    "Cycle Tracker: rejected spreadsheet ID input %r; paste only"
                    " the long ID from the sheet URL",
                    raw_spreadsheet_id,
                )
                errors["base"] = "invalid_spreadsheet_id"
            else:
                poll_interval = _clamp_poll_interval(user_input[CONF_POLL_INTERVAL])

                result = await _async_validate_sheet(
                    self.hass,
                    spreadsheet_id,
                    worksheet,
                    service_account_file,
                )
                if result.client_email:
                    self._sheet_account_email = result.client_email
                if result.error:
                    errors["base"] = result.error
                else:
                    self._sheet_input = {
                        CONF_SPREADSHEET_ID: spreadsheet_id,
                        CONF_WORKSHEET: worksheet,
                        CONF_SERVICE_ACCOUNT_FILE: service_account_file,
                        CONF_POLL_INTERVAL: poll_interval,
                    }
                    if result.data_rows == 0:
                        cached = await _async_local_cached_periods(self.hass)
                        if cached:
                            return await self.async_step_import_offer()
                    return self._create_sheet_entry()

        return self.async_show_form(
            step_id="sheet",
            data_schema=_sheet_schema(self.hass),
            errors=errors,
            description_placeholders={
                "client_email": self._sheet_account_email or "—",
                # Compatibility placeholder: browsers may still render a cached
                # older translation that interpolates {account_hint}.
                "account_hint": self._sheet_account_email or "—",
            },
        )

    async def async_step_import_offer(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer a one-time import of cached periods into the empty sheet."""
        if user_input is None:
            return self.async_show_form(
                step_id="import_offer",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_IMPORT_CACHED,
                            default=False,
                        ): selector.BooleanSelector(),
                    }
                ),
            )
        if user_input.get(CONF_IMPORT_CACHED):
            assert self._sheet_input is not None
            await self._async_import_cached_periods()
        return self._create_sheet_entry()

    async def _async_import_cached_periods(self) -> None:
        """Import local periods into the validated empty sheet."""
        assert self._sheet_input is not None
        path = _resolve_service_account_path(
            self.hass, self._sheet_input[CONF_SERVICE_ACCOUNT_FILE]
        )
        if path is None:
            return
        service_account_info = await self.hass.async_add_executor_job(
            _load_service_account_key, path
        )
        client = SheetsClient(self.hass, service_account_info)
        repo = SheetsPeriodRepository(
            client,
            self._sheet_input[CONF_SPREADSHEET_ID],
            self._sheet_input[CONF_WORKSHEET],
        )
        cached = await _async_local_cached_periods(self.hass)
        await import_cached_periods(repo, cached)

    def _create_sheet_entry(self) -> ConfigFlowResult:
        """Persist the config entry with the validated sheet settings."""
        assert self._sheet_input is not None
        self._data.update(self._sheet_input)
        return self.async_create_entry(title="Cycle Tracker", data=self._data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> CycleTrackerOptionsFlow:
        """Get the options flow."""
        return CycleTrackerOptionsFlow()


class CycleTrackerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Cycle Tracker.

    Home Assistant creates the flow through ``OptionsFlowManager``, which is
    also the only place where ``OptionsFlow.config_entry`` becomes available, so the
    tests drive the dialog through ``hass.config_entries.options`` instead of
    constructing the flow themselves.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        entry = self.config_entry
        if user_input is not None:
            raw_spreadsheet_id = str(user_input[CONF_SPREADSHEET_ID])
            spreadsheet_id = _normalize_spreadsheet_id(raw_spreadsheet_id)
            worksheet = str(user_input[CONF_WORKSHEET]).strip()
            service_account_file = str(user_input[CONF_SERVICE_ACCOUNT_FILE]).strip()
            if spreadsheet_id is None:
                _LOGGER.warning(
                    "Cycle Tracker: rejected spreadsheet ID input %r; paste only"
                    " the long ID from the sheet URL",
                    raw_spreadsheet_id,
                )
                errors["base"] = "invalid_spreadsheet_id"
            else:
                sheet_data: dict[str, Any] = {
                    CONF_SPREADSHEET_ID: spreadsheet_id,
                    CONF_WORKSHEET: worksheet,
                    CONF_SERVICE_ACCOUNT_FILE: service_account_file,
                    CONF_POLL_INTERVAL: _clamp_poll_interval(
                        user_input[CONF_POLL_INTERVAL]
                    ),
                }
                result = await _async_validate_sheet(
                    self.hass,
                    sheet_data[CONF_SPREADSHEET_ID],
                    sheet_data[CONF_WORKSHEET],
                    sheet_data[CONF_SERVICE_ACCOUNT_FILE],
                )
                if result.error:
                    errors["base"] = result.error
                else:
                    return self.async_create_entry(
                        title="",
                        data={**user_input, **sheet_data},
                    )

        defaults = {
            CONF_CYCLE_LENGTH: _setting(entry, CONF_CYCLE_LENGTH, DEFAULT_CYCLE_LENGTH),
            CONF_PERIOD_LENGTH: _setting(
                entry, CONF_PERIOD_LENGTH, DEFAULT_PERIOD_LENGTH
            ),
            CONF_PREDICTION_ALGORITHM: _setting(
                entry, CONF_PREDICTION_ALGORITHM, DEFAULT_PREDICTION_ALGORITHM
            ),
            CONF_NOTIFICATION_OFFSET_DAYS: _setting(
                entry,
                CONF_NOTIFICATION_OFFSET_DAYS,
                DEFAULT_NOTIFICATION_OFFSET_DAYS,
            ),
            CONF_ENABLE_NOTIFICATIONS: _setting(
                entry, CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS
            ),
            CONF_NOTIFICATION_TIME: _setting(
                entry, CONF_NOTIFICATION_TIME, DEFAULT_NOTIFICATION_TIME
            ),
            CONF_SPREADSHEET_ID: _setting(entry, CONF_SPREADSHEET_ID, ""),
            CONF_WORKSHEET: _setting(entry, CONF_WORKSHEET, "Sheet1"),
            CONF_SERVICE_ACCOUNT_FILE: _setting(entry, CONF_SERVICE_ACCOUNT_FILE, ""),
            CONF_POLL_INTERVAL: _setting(
                entry, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL_MINUTES
            ),
        }
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CYCLE_LENGTH,
                        default=defaults[CONF_CYCLE_LENGTH],
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=20,
                            max=45,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_PERIOD_LENGTH,
                        default=defaults[CONF_PERIOD_LENGTH],
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=2,
                            max=10,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_PREDICTION_ALGORITHM,
                        default=defaults[CONF_PREDICTION_ALGORITHM],
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=PREDICTION_ALGORITHMS,
                            translation_key="prediction_algorithm",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_NOTIFICATION_OFFSET_DAYS,
                        default=defaults[CONF_NOTIFICATION_OFFSET_DAYS],
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=14,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_ENABLE_NOTIFICATIONS,
                        default=defaults[CONF_ENABLE_NOTIFICATIONS],
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_NOTIFICATION_TIME,
                        default=defaults[CONF_NOTIFICATION_TIME],
                    ): selector.TimeSelector(),
                    vol.Required(
                        CONF_SPREADSHEET_ID,
                        default=defaults[CONF_SPREADSHEET_ID],
                    ): str,
                    vol.Required(
                        CONF_WORKSHEET,
                        default=defaults[CONF_WORKSHEET],
                    ): str,
                    vol.Required(
                        CONF_SERVICE_ACCOUNT_FILE,
                        default=defaults[CONF_SERVICE_ACCOUNT_FILE],
                    ): str,
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=defaults[CONF_POLL_INTERVAL],
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_POLL_INTERVAL_MINUTES,
                            max=MAX_POLL_INTERVAL_MINUTES,
                            step=1,
                            unit_of_measurement="minutes",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            errors=errors,
        )
