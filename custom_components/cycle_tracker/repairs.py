"""Repair-issue helpers for Cycle Tracker sheet sync problems."""

from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)

from .const import DOMAIN
from .repository import SheetSchemaError
from .sheets import ServiceAccountAccessTokenError, SheetsApiError

ISSUE_SHEET_NOT_CONFIGURED = "sheet_not_configured"
ISSUE_SHEET_AUTH_FAILED = "sheet_auth_failed"
ISSUE_SHEET_UNREACHABLE = "sheet_unreachable"
ISSUE_SHEET_SCHEMA_INVALID = "sheet_schema_invalid"
ISSUE_SHEET_ROWS_INVALID = "sheet_rows_invalid"

_SHEET_ISSUE_IDS = {
    ISSUE_SHEET_NOT_CONFIGURED,
    ISSUE_SHEET_AUTH_FAILED,
    ISSUE_SHEET_UNREACHABLE,
    ISSUE_SHEET_SCHEMA_INVALID,
    ISSUE_SHEET_ROWS_INVALID,
}


def _sheets_api_status(exc: SheetsApiError) -> int:
    """Extract the HTTP status from a SheetsApiError payload."""
    body: dict[str, Any] = exc.args[0] if exc.args else {}
    return body.get("error", {}).get("code", 0)


def classify_sheet_exception(exc: Exception) -> str:
    """Map an exception to one of the stable sheet repair issue ids."""
    if isinstance(exc, SheetSchemaError):
        return ISSUE_SHEET_SCHEMA_INVALID
    if isinstance(exc, ServiceAccountAccessTokenError):
        return ISSUE_SHEET_AUTH_FAILED
    if isinstance(exc, SheetsApiError):
        status = _sheets_api_status(exc)
        if status in (401, 403):
            return ISSUE_SHEET_AUTH_FAILED
        if status in (404,):
            return ISSUE_SHEET_UNREACHABLE
        return ISSUE_SHEET_UNREACHABLE
    if isinstance(exc, (aiohttp.ClientError, TimeoutError)):
        return ISSUE_SHEET_UNREACHABLE
    return ISSUE_SHEET_UNREACHABLE


def async_create_sheet_issue(
    hass: HomeAssistant,
    issue_id: str,
    placeholders: dict[str, str] | None = None,
) -> None:
    """Create a sheet-related repair issue, if it is a known kind."""
    if issue_id not in _SHEET_ISSUE_IDS:
        return
    async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=True,
        severity=IssueSeverity.WARNING,
        translation_key=issue_id,
        translation_placeholders=placeholders or {},
    )


def async_delete_sheet_issue(hass: HomeAssistant, issue_id: str) -> None:
    """Delete a sheet-related repair issue, if it is a known kind."""
    if issue_id not in _SHEET_ISSUE_IDS:
        return
    async_delete_issue(hass, DOMAIN, issue_id)


def async_clear_sheet_issues(hass: HomeAssistant, keep: set[str] | None = None) -> None:
    """Clear all sheet issues except those in ``keep``."""
    keep = keep or set()
    for issue_id in _SHEET_ISSUE_IDS - keep:
        async_delete_sheet_issue(hass, issue_id)
