"""Tests for the Google Sheets service-account adapter."""

from __future__ import annotations

import re
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from homeassistant.core import HomeAssistant

from custom_components.cycle_tracker.sheets import SheetsApiError, SheetsClient

TOKEN_URL = "https://oauth2.googleapis.com/token"
SPREADSHEET_ID = "sheet1"
WORKSHEET = "Sheet1"
SHEET_ID = 42
SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
SHEETS_RE = re.compile(
    r"https://sheets\.googleapis\.com/v4/spreadsheets/[^/]+/values/[^/]+"
)
# The spreadsheets.get lookup has no /values/ segment and carries a field mask
# in the query string, so it needs its own matcher (query params follow the path).
GET_SPREADSHEET_RE = re.compile(
    r"https://sheets\.googleapis\.com/v4/spreadsheets/[^/?]+"
)
BATCH_UPDATE_RE = re.compile(
    r"https://sheets\.googleapis\.com/v4/spreadsheets/[^/]+:batchUpdate"
)
FIELD_MASK = "sheets.properties.title,sheets.properties.sheetId"


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


def _batch_update_calls(aioclient_mock):
    """Return all recorded batchUpdate calls."""
    return [
        call
        for call in aioclient_mock.mock_calls
        if call[0].lower() == "post" and ":batchUpdate" in str(call[1])
    ]


def _batch_update_call(aioclient_mock):
    """Return the single recorded batchUpdate call as (method, url, body, headers)."""
    calls = _batch_update_calls(aioclient_mock)
    assert len(calls) == 1
    return calls[0]


def _get_spreadsheet_call(aioclient_mock):
    """Return the single field-masked spreadsheets.get call made by insert_row."""
    calls = [
        call
        for call in aioclient_mock.mock_calls
        if call[0].lower() == "get"
        and "/spreadsheets/" in str(call[1])
        and "/values/" not in str(call[1])
    ]
    assert len(calls) == 1
    return calls[0]


def _mock_sheet_lookup(aioclient_mock, json_body=None) -> None:
    """Register the field-masked spreadsheets.get with a default matching sheet."""
    if json_body is None:
        json_body = {
            "sheets": [{"properties": {"title": WORKSHEET, "sheetId": SHEET_ID}}]
        }
    aioclient_mock.get(GET_SPREADSHEET_RE, json=json_body)


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


async def test_non_json_error_body_raises_sheets_api_error(
    hass: HomeAssistant,
    aioclient_mock,
) -> None:
    """A text/html 400 surfaces as SheetsApiError instead of a ContentTypeError."""
    aioclient_mock.post(TOKEN_URL, json=_token_response())
    aioclient_mock.get(
        SHEETS_RE,
        status=400,
        text="<html><body>Bad Request</body></html>",
        headers={"Content-Type": "text/html; charset=UTF-8"},
    )

    client = SheetsClient(hass, _service_account_info())
    with pytest.raises(SheetsApiError) as excinfo:
        await client.read_rows(SPREADSHEET_ID, WORKSHEET)

    error = excinfo.value.args[0]["error"]
    assert error["code"] == 400
    assert "Bad Request" in error["message"]


async def test_insert_row_resolves_sheet_id_then_posts_dimension_range(
    hass: HomeAssistant,
    aioclient_mock,
) -> None:
    """insert_row looks up the numeric sheetId, then inserts a row below the header."""
    aioclient_mock.post(TOKEN_URL, json=_token_response())
    _mock_sheet_lookup(aioclient_mock)
    aioclient_mock.post(BATCH_UPDATE_RE, json={})

    client = SheetsClient(hass, _service_account_info())
    await client.insert_row(SPREADSHEET_ID, WORKSHEET)

    # 1. Field-masked spreadsheets.get resolves the worksheet title to a sheetId.
    get_method, get_url, get_data, get_headers = _get_spreadsheet_call(aioclient_mock)
    assert get_method == "GET"
    assert get_url.path == f"/v4/spreadsheets/{SPREADSHEET_ID}"
    assert get_url.query["fields"] == FIELD_MASK
    assert get_data is None
    assert get_headers["Authorization"] == "Bearer TOKEN123"

    # 2. batchUpdate inserts one row at row 2 using a DimensionRange object.
    method, url, body, headers = _batch_update_call(aioclient_mock)
    assert method == "POST"
    assert str(url) == f"{SHEETS_API_BASE}/{SPREADSHEET_ID}:batchUpdate"
    assert headers["Authorization"] == "Bearer TOKEN123"
    assert body == {
        "requests": [
            {
                "insertDimension": {
                    "range": {
                        "sheetId": SHEET_ID,
                        "dimension": "ROWS",
                        "startIndex": 1,
                        "endIndex": 2,
                    },
                    "inheritFromBefore": False,
                }
            }
        ]
    }


async def test_insert_row_skips_other_sheets_when_resolving_id(
    hass: HomeAssistant,
    aioclient_mock,
) -> None:
    """The sheetId comes from the sheet whose title matches the worksheet."""
    aioclient_mock.post(TOKEN_URL, json=_token_response())
    _mock_sheet_lookup(
        aioclient_mock,
        json_body={
            "sheets": [
                {"properties": {"title": "Other", "sheetId": 7}},
                {"properties": {"title": WORKSHEET, "sheetId": SHEET_ID}},
            ]
        },
    )
    aioclient_mock.post(BATCH_UPDATE_RE, json={})

    client = SheetsClient(hass, _service_account_info())
    await client.insert_row(SPREADSHEET_ID, WORKSHEET)

    body = _batch_update_call(aioclient_mock)[2]
    assert body["requests"][0]["insertDimension"]["range"]["sheetId"] == SHEET_ID


async def test_insert_row_no_matching_worksheet_raises_sheets_api_error(
    hass: HomeAssistant,
    aioclient_mock,
) -> None:
    """When no sheet title matches the worksheet, no batchUpdate is attempted."""
    aioclient_mock.post(TOKEN_URL, json=_token_response())
    _mock_sheet_lookup(
        aioclient_mock,
        json_body={"sheets": [{"properties": {"title": "Other", "sheetId": 7}}]},
    )

    client = SheetsClient(hass, _service_account_info())
    with pytest.raises(SheetsApiError, match="not found"):
        await client.insert_row(SPREADSHEET_ID, WORKSHEET)

    assert _batch_update_calls(aioclient_mock) == []


@pytest.mark.parametrize(
    "bad_body",
    [
        {},  # missing 'sheets'
        {"sheets": {}},  # 'sheets' is not a list
        {"sheets": ["not-a-dict"]},  # sheet entry is not an object
        {"sheets": [{"title": WORKSHEET}]},  # missing 'properties'
        {"sheets": [{"properties": "not-a-dict"}]},  # 'properties' is not an object
        {"sheets": [{"properties": {"title": WORKSHEET}}]},  # missing 'sheetId'
        {"sheets": [{"properties": {"title": WORKSHEET, "sheetId": "42"}}]},  # bad id
    ],
)
async def test_insert_row_malformed_sheet_lookup_raises_sheets_api_error(
    hass: HomeAssistant,
    aioclient_mock,
    bad_body,
) -> None:
    """A malformed/missing sheets[].properties payload surfaces as SheetsApiError."""
    aioclient_mock.post(TOKEN_URL, json=_token_response())
    _mock_sheet_lookup(aioclient_mock, json_body=bad_body)

    client = SheetsClient(hass, _service_account_info())
    with pytest.raises(SheetsApiError):
        await client.insert_row(SPREADSHEET_ID, WORKSHEET)

    assert _batch_update_calls(aioclient_mock) == []


@pytest.mark.parametrize("failing_call", ["get", "batch"])
async def test_insert_row_non_json_error_raises_sheets_api_error(
    hass: HomeAssistant,
    aioclient_mock,
    failing_call,
) -> None:
    """A non-JSON error on either call surfaces as SheetsApiError, like other writes."""
    aioclient_mock.post(TOKEN_URL, json=_token_response())
    if failing_call == "get":
        aioclient_mock.get(
            GET_SPREADSHEET_RE,
            status=500,
            text="<html><body>Server Error</body></html>",
            headers={"Content-Type": "text/html; charset=UTF-8"},
        )
    else:
        _mock_sheet_lookup(aioclient_mock)
        aioclient_mock.post(
            BATCH_UPDATE_RE,
            status=500,
            text="<html><body>Server Error</body></html>",
            headers={"Content-Type": "text/html; charset=UTF-8"},
        )

    client = SheetsClient(hass, _service_account_info())
    with pytest.raises(SheetsApiError) as excinfo:
        await client.insert_row(SPREADSHEET_ID, WORKSHEET)

    error = excinfo.value.args[0]["error"]
    assert error["code"] == 500
    assert "Server Error" in error["message"]
