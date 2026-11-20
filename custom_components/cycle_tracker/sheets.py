"""Async Google Sheets client using a service-account JSON key.

The client implements the service-account JWT flow manually with the
``cryptography`` library, exchanges the signed assertion for an access token,
and caches that token until it is within one minute of expiry.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any

import aiohttp
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

TOKEN_URI = "https://oauth2.googleapis.com/token"
SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
TOKEN_LEEWAY_SECONDS = 60


class ServiceAccountAccessTokenError(Exception):
    """Obtaining a Google access token failed."""


class SheetsApiError(Exception):
    """The Google Sheets API returned an error response."""


class SheetsClient:
    """Async Google Sheets client backed by a service account."""

    def __init__(
        self,
        hass: HomeAssistant,
        service_account_info: dict[str, str],
    ) -> None:
        """Initialize the client from a parsed service-account key JSON dict."""
        self._hass = hass
        self._client_email = service_account_info["client_email"]
        self._token_uri = service_account_info["token_uri"]

        private_key_pem = service_account_info["private_key"].encode("utf-8")
        private_key = serialization.load_pem_private_key(private_key_pem, password=None)
        if not isinstance(private_key, RSAPrivateKey):
            raise TypeError("Service account private key must be an RSA key")
        self._private_key = private_key

        self._session = async_get_clientsession(hass)
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    def _jwt_assertion(self) -> str:
        """Build and sign a RS256 JWT assertion for the service account."""
        now = int(time.time())
        header = _b64url_encode(
            json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode()
        )
        payload = _b64url_encode(
            json.dumps(
                {
                    "iss": self._client_email,
                    "sub": self._client_email,
                    "scope": SHEETS_SCOPE,
                    "aud": self._token_uri,
                    "iat": now,
                    "exp": now + 3600,
                },
                separators=(",", ":"),
            ).encode()
        )
        signing_input = f"{header}.{payload}".encode()
        signature = self._private_key.sign(
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return f"{header}.{payload}.{_b64url_encode(signature)}"

    async def _ensure_token(self) -> str:
        """Return a valid access token, reusing the cached one when possible."""
        if (
            self._access_token is not None
            and time.monotonic() < self._expires_at - TOKEN_LEEWAY_SECONDS
        ):
            return self._access_token

        assertion = self._jwt_assertion()
        async with self._session.post(
            self._token_uri,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        ) as resp:
            body = await _json_body(resp)
            if resp.status != 200:
                raise ServiceAccountAccessTokenError(body)

        self._access_token = body["access_token"]
        self._expires_at = time.monotonic() + body["expires_in"]
        return self._access_token

    async def read_rows(
        self,
        spreadsheet_id: str,
        worksheet: str,
    ) -> list[list[Any]]:
        """Return the raw grid from a worksheet as ``list[list[Any]]``.

        Dates and numbers are requested with ``UNFORMATTED_VALUE`` so they
        arrive as serials or strings rather than rendered text.
        """
        token = await self._ensure_token()
        url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{worksheet}"
        async with self._session.get(
            url,
            params={"valueRenderOption": "UNFORMATTED_VALUE"},
            headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            body = await _json_body(resp)
            if resp.status != 200:
                raise SheetsApiError(body)
        return body.get("values", [])

    async def insert_row(
        self,
        spreadsheet_id: str,
        worksheet: str,
    ) -> None:
        """Insert one blank row directly below the header (row 2).

        Resolve the worksheet name to a numeric sheetId first because
        ``InsertDimensionRequest`` addresses sheets by id, not by name.
        """
        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}"}

        get_url = f"{SHEETS_API_BASE}/{spreadsheet_id}"
        async with self._session.get(
            get_url,
            params={"fields": "sheets.properties.title,sheets.properties.sheetId"},
            headers=headers,
        ) as resp:
            body = await _json_body(resp)
            if resp.status != 200:
                raise SheetsApiError(body)

        sheets = body.get("sheets")
        if not isinstance(sheets, list):
            raise SheetsApiError(
                f"Missing or invalid 'sheets' in response for spreadsheet {spreadsheet_id!r}"
            )

        sheet_id: int | None = None
        for sheet in sheets:
            properties = sheet.get("properties") if isinstance(sheet, dict) else None
            if not isinstance(properties, dict):
                raise SheetsApiError(
                    f"Missing or invalid sheet properties in spreadsheet {spreadsheet_id!r}"
                )
            if properties.get("title") != worksheet:
                continue
            candidate = properties.get("sheetId")
            if not isinstance(candidate, int) or isinstance(candidate, bool):
                raise SheetsApiError(
                    f"Worksheet {worksheet!r} has a missing or invalid sheetId"
                )
            sheet_id = candidate
            break

        if sheet_id is None:
            raise SheetsApiError(
                f"Worksheet {worksheet!r} not found in spreadsheet {spreadsheet_id!r}"
            )

        url = f"{SHEETS_API_BASE}/{spreadsheet_id}:batchUpdate"
        async with self._session.post(
            url,
            headers=headers,
            json={
                "requests": [
                    {
                        "insertDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": 1,
                                "endIndex": 2,
                            },
                            "inheritFromBefore": False,
                        }
                    }
                ]
            },
        ) as resp:
            body = await _json_body(resp)
            if resp.status != 200:
                raise SheetsApiError(body)

    async def append_row(
        self,
        spreadsheet_id: str,
        worksheet: str,
        values: list[Any],
    ) -> None:
        """Append a single row to the worksheet using ``valueInputOption=RAW``."""
        token = await self._ensure_token()
        last_col = _column_letter(len(values) - 1)
        range_spec = f"{worksheet}!A1:{last_col}1"
        url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_spec}:append"
        async with self._session.post(
            url,
            params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
            headers={"Authorization": f"Bearer {token}"},
            json={"values": [values]},
        ) as resp:
            body = await _json_body(resp)
            if resp.status != 200:
                raise SheetsApiError(body)

    async def update_row(
        self,
        spreadsheet_id: str,
        worksheet: str,
        row_index: int,
        values: list[Any],
    ) -> None:
        """Overwrite one worksheet row using ``valueInputOption=RAW``."""
        token = await self._ensure_token()
        last_col = _column_letter(len(values) - 1)
        range_spec = f"{worksheet}!A{row_index}:{last_col}{row_index}"
        url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_spec}"
        async with self._session.put(
            url,
            params={"valueInputOption": "RAW"},
            headers={"Authorization": f"Bearer {token}"},
            json={"values": [values]},
        ) as resp:
            body = await _json_body(resp)
            if resp.status != 200:
                raise SheetsApiError(body)

    async def clear_row(
        self,
        spreadsheet_id: str,
        worksheet: str,
        row_index: int,
        width: int = 6,
    ) -> None:
        """Clear one worksheet row to blank cells."""
        token = await self._ensure_token()
        last_col = _column_letter(width - 1)
        range_spec = f"{worksheet}!A{row_index}:{last_col}{row_index}"
        url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_spec}:clear"
        async with self._session.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            body = await _json_body(resp)
            if resp.status != 200:
                raise SheetsApiError(body)


async def _json_body(resp: aiohttp.ClientResponse) -> dict[str, Any]:
    """Decode a JSON body, falling back to an error-shaped dict for non-JSON replies."""
    try:
        body = await resp.json(content_type=None)
    except (json.JSONDecodeError, TypeError, ValueError):
        text = await resp.text()
        return {"error": {"code": resp.status, "message": text[:200]}}
    if isinstance(body, dict):
        return body
    return {"error": {"code": resp.status, "message": str(body)[:200]}}


def _column_letter(index: int) -> str:
    """Convert a zero-based column index to an A1-style column letter."""
    result = ""
    while index >= 0:
        result = chr(ord("A") + (index % 26)) + result
        index = index // 26 - 1
    return result


def _b64url_encode(data: bytes) -> str:
    """Return a base64url-encoded string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
