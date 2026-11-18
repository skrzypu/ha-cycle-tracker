"""Tests for the Google Sheets service-account adapter."""

from __future__ import annotations

import re
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from homeassistant.core import HomeAssistant

from custom_components.cycle_tracker.sheets import SheetsClient

TOKEN_URL = "https://oauth2.googleapis.com/token"
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
        "token_uri": TOKEN_URL,
    }


def _token_response() -> dict[str, Any]:
    """Return a mocked OAuth2 token response."""
    return {
        "access_token": "TOKEN123",
        "expires_in": 3600,
        "token_type": "Bearer",
    }


def _token_call_count(aioclient_mock) -> int:
    """Count how many times the OAuth2 token endpoint was POSTed."""
    return sum(
        1
        for call in aioclient_mock.mock_calls
        if call[0] == "POST" and TOKEN_URL in str(call[1])
    )


@pytest.fixture
def sheets_client(hass: HomeAssistant) -> SheetsClient:
    """Return a SheetsClient wired to a generated service-account key."""
    return SheetsClient(hass, _service_account_info())


async def test_access_token_reused_across_calls(
    hass: HomeAssistant,
    aioclient_mock,
) -> None:
    """Two read_rows calls before expiry hit the token endpoint only once."""
    aioclient_mock.post(TOKEN_URL, json=_token_response())
    aioclient_mock.get(SHEETS_RE, json={"values": [["header"]]})

    client = SheetsClient(hass, _service_account_info())
    await client.read_rows(SPREADSHEET_ID, WORKSHEET)
    await client.read_rows(SPREADSHEET_ID, WORKSHEET)

    assert _token_call_count(aioclient_mock) == 1


async def test_read_rows_returns_header_and_data_rows(
    hass: HomeAssistant,
    aioclient_mock,
) -> None:
    """read_rows returns the header row followed by data rows unmodified."""
    aioclient_mock.post(TOKEN_URL, json=_token_response())
    aioclient_mock.get(
        SHEETS_RE,
        json={
            "values": [
                ["start_date", "flow_intensity"],
                ["2026-01-01", "medium"],
            ]
        },
    )

    client = SheetsClient(hass, _service_account_info())
    rows = await client.read_rows(SPREADSHEET_ID, WORKSHEET)

    assert rows == [
        ["start_date", "flow_intensity"],
        ["2026-01-01", "medium"],
    ]
