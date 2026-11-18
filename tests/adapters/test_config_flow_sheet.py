"""Tests for the Google Sheets source-of-truth config flow step."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import (
    CONF_CYCLE_LENGTH,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_LAST_PERIOD_START,
    CONF_NOTIFICATION_OFFSET_DAYS,
    CONF_NOTIFICATION_TIME,
    CONF_PERIOD_LENGTH,
    CONF_POLL_INTERVAL,
    CONF_PREDICTION_ALGORITHM,
    CONF_SERVICE_ACCOUNT_FILE,
    CONF_SPREADSHEET_ID,
    CONF_WORKSHEET,
    DOMAIN,
)
from custom_components.cycle_tracker.sheets import TOKEN_URI

SPREADSHEET_ID = "sheet1"
WORKSHEET = "Sheet1"
SHEETS_RE = re.compile(
    r"https://sheets\.googleapis\.com/v4/spreadsheets/[^/]+/values/[^/]+"
)


def _service_account_info() -> dict[str, str]:
    """Return a minimal service-account dict with a generated RSA private key."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return {
        "type": "service_account",
        "client_email": "test@example.iam.gserviceaccount.com",
        "private_key": pem,
        "token_uri": TOKEN_URI,
    }


def _token_response() -> dict[str, Any]:
    """Return a mocked OAuth2 token response."""
    return {
        "access_token": "TOKEN123",
        "expires_in": 3600,
        "token_type": "Bearer",
    }


def _write_key_file(hass: HomeAssistant) -> str:
    """Write a service-account key file inside the test config directory."""
    config_dir = Path(hass.config.config_dir)
    key_path = config_dir / "cycle_tracker_service_account.json"
    key_path.write_text(json.dumps(_service_account_info()), encoding="utf-8")
    return str(key_path)


async def _drive_to_sheet_step(
    hass: HomeAssistant,
    aioclient_mock: Any,
) -> dict[str, Any]:
    """Progress the config flow to the sheet step and return its result."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CYCLE_LENGTH: 28,
            CONF_PERIOD_LENGTH: 5,
            CONF_LAST_PERIOD_START: "2026-01-01",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "preferences"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_PREDICTION_ALGORITHM: "weighted_moving_average",
            CONF_NOTIFICATION_OFFSET_DAYS: 2,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "notifications"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_ENABLE_NOTIFICATIONS: False,
            CONF_NOTIFICATION_TIME: "08:00",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sheet"
    return result


async def test_sheet_step_rejects_missing_required_column(
    hass: HomeAssistant,
    aioclient_mock: Any,
) -> None:
    """A worksheet header without all required columns fails with invalid_schema."""
    result = await _drive_to_sheet_step(hass, aioclient_mock)
    aioclient_mock.post(TOKEN_URI, json=_token_response())
    aioclient_mock.get(
        SHEETS_RE,
        json={"values": [["period_id", "start_date"]]},
    )
    key_path = _write_key_file(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SPREADSHEET_ID: SPREADSHEET_ID,
            CONF_WORKSHEET: WORKSHEET,
            CONF_SERVICE_ACCOUNT_FILE: key_path,
            CONF_POLL_INTERVAL: 5,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sheet"
    assert result["errors"] == {"base": "invalid_schema"}


async def test_sheet_step_accepts_valid_header_and_creates_entry(
    hass: HomeAssistant,
    aioclient_mock: Any,
) -> None:
    """A valid header creates the entry with the four sheet keys."""
    result = await _drive_to_sheet_step(hass, aioclient_mock)
    aioclient_mock.post(TOKEN_URI, json=_token_response())
    aioclient_mock.get(
        SHEETS_RE,
        json={
            "values": [
                [
                    "period_id",
                    "start_date",
                    "end_date",
                    "flow_intensity",
                    "notes",
                    "updated_at",
                ]
            ]
        },
    )
    key_path = _write_key_file(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SPREADSHEET_ID: SPREADSHEET_ID,
            CONF_WORKSHEET: WORKSHEET,
            CONF_SERVICE_ACCOUNT_FILE: key_path,
            CONF_POLL_INTERVAL: 10,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry: MockConfigEntry = result["result"]
    assert entry.data[CONF_SPREADSHEET_ID] == SPREADSHEET_ID
    assert entry.data[CONF_WORKSHEET] == WORKSHEET
    assert entry.data[CONF_SERVICE_ACCOUNT_FILE] == key_path
    assert entry.data[CONF_POLL_INTERVAL] == 10


async def test_sheet_step_rejects_key_path_outside_config_dir(
    hass: HomeAssistant,
    aioclient_mock: Any,
) -> None:
    """A service-account key path outside the config directory is rejected."""
    result = await _drive_to_sheet_step(hass, aioclient_mock)
    key_path = "/tmp/evil_service_account.json"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SPREADSHEET_ID: SPREADSHEET_ID,
            CONF_WORKSHEET: WORKSHEET,
            CONF_SERVICE_ACCOUNT_FILE: key_path,
            CONF_POLL_INTERVAL: 5,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sheet"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_sheet_step_offers_import_for_empty_sheet_with_local_cache(
    hass: HomeAssistant,
    aioclient_mock: Any,
) -> None:
    """An empty sheet + local cache shows the import offer, then writes rows."""
    from homeassistant.helpers.storage import Store

    from custom_components.cycle_tracker.const import STORAGE_KEY, STORAGE_VERSION
    from custom_components.cycle_tracker.domain.models import legacy_period_id
    from custom_components.cycle_tracker.repository import LocalStoreRepository

    APPEND_RE = re.compile(
        r"https://sheets\.googleapis\.com/v4/spreadsheets/[^/]+/values/[^/]+:append"
    )

    # Seed the legacy local store with one period.
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_save(
        {
            "periods": [
                {
                    "period_id": str(legacy_period_id(date(2026, 1, 1))),
                    "start_date": "2026-01-01",
                    "end_date": "2026-01-05",
                    "flow_intensity": "medium",
                    "notes": None,
                    "updated_at": None,
                }
            ]
        }
    )
    cached = await LocalStoreRepository(hass).read_all()
    assert len(cached) == 1

    result = await _drive_to_sheet_step(hass, aioclient_mock)
    aioclient_mock.post(TOKEN_URI, json=_token_response())
    # Validation read and upsert read both match the first GET mock.
    aioclient_mock.get(
        SHEETS_RE,
        json={
            "values": [
                [
                    "period_id",
                    "start_date",
                    "end_date",
                    "flow_intensity",
                    "notes",
                    "updated_at",
                ]
            ]
        },
    )
    aioclient_mock.post(APPEND_RE, status=200, json={})
    key_path = _write_key_file(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SPREADSHEET_ID: SPREADSHEET_ID,
            CONF_WORKSHEET: WORKSHEET,
            CONF_SERVICE_ACCOUNT_FILE: key_path,
            CONF_POLL_INTERVAL: 5,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "import_offer"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"import_cached_periods": True},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry: MockConfigEntry = result["result"]
    assert entry.data[CONF_SPREADSHEET_ID] == SPREADSHEET_ID


async def test_sheet_step_declining_import_writes_no_rows(
    hass: HomeAssistant,
    aioclient_mock: Any,
) -> None:
    """Declining the import offer creates the entry without writing any rows."""
    from homeassistant.helpers.storage import Store

    from custom_components.cycle_tracker.const import STORAGE_KEY, STORAGE_VERSION
    from custom_components.cycle_tracker.domain.models import legacy_period_id
    from custom_components.cycle_tracker.repository import LocalStoreRepository

    APPEND_RE = re.compile(
        r"https://sheets\.googleapis\.com/v4/spreadsheets/[^/]+/values/[^/]+:append"
    )

    # Seed the legacy local store with one cached period so the import is offered.
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_save(
        {
            "periods": [
                {
                    "period_id": str(legacy_period_id(date(2026, 1, 1))),
                    "start_date": "2026-01-01",
                    "end_date": "2026-01-05",
                    "flow_intensity": "medium",
                    "notes": None,
                    "updated_at": None,
                }
            ]
        }
    )
    cached = await LocalStoreRepository(hass).read_all()
    assert len(cached) == 1

    result = await _drive_to_sheet_step(hass, aioclient_mock)
    aioclient_mock.post(TOKEN_URI, json=_token_response())
    aioclient_mock.get(
        SHEETS_RE,
        json={
            "values": [
                [
                    "period_id",
                    "start_date",
                    "end_date",
                    "flow_intensity",
                    "notes",
                    "updated_at",
                ]
            ]
        },
    )
    aioclient_mock.post(APPEND_RE, status=200, json={})
    key_path = _write_key_file(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SPREADSHEET_ID: SPREADSHEET_ID,
            CONF_WORKSHEET: WORKSHEET,
            CONF_SERVICE_ACCOUNT_FILE: key_path,
            CONF_POLL_INTERVAL: 5,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "import_offer"

    # Decline the one-time import.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"import_cached_periods": False},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry: MockConfigEntry = result["result"]
    assert entry.data[CONF_SPREADSHEET_ID] == SPREADSHEET_ID

    # Declining must write nothing to the sheet: no append, no update.
    assert not any(":append" in str(call[1]) for call in aioclient_mock.mock_calls)
    assert not any(call[0] == "PUT" for call in aioclient_mock.mock_calls)


async def test_sheet_step_maps_auth_error_to_invalid_auth(
    hass: HomeAssistant,
    aioclient_mock: Any,
) -> None:
    """A rejected token exchange surfaces as invalid_auth."""
    result = await _drive_to_sheet_step(hass, aioclient_mock)
    aioclient_mock.post(
        TOKEN_URI,
        status=400,
        json={"error": "invalid_grant"},
    )
    key_path = _write_key_file(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SPREADSHEET_ID: SPREADSHEET_ID,
            CONF_WORKSHEET: WORKSHEET,
            CONF_SERVICE_ACCOUNT_FILE: key_path,
            CONF_POLL_INTERVAL: 5,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sheet"
    assert result["errors"] == {"base": "invalid_auth"}
