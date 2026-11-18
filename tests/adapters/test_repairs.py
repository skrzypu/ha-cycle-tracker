"""Tests for sheet-sync repair issues."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.issue_registry import async_get
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import (
    CONF_POLL_INTERVAL,
    CONF_SERVICE_ACCOUNT_FILE,
    CONF_SPREADSHEET_ID,
    CONF_WORKSHEET,
    DOMAIN,
)
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator
from custom_components.cycle_tracker.domain.models import Period
from custom_components.cycle_tracker.repairs import (
    ISSUE_SHEET_AUTH_FAILED,
    ISSUE_SHEET_ROWS_INVALID,
)
from custom_components.cycle_tracker.sheets import ServiceAccountAccessTokenError


def _sheet_entry_data(key_path: str) -> dict[str, Any]:
    """Return config entry data with sheet settings."""
    return {
        CONF_SPREADSHEET_ID: "sheet1",
        CONF_WORKSHEET: "Sheet1",
        CONF_SERVICE_ACCOUNT_FILE: key_path,
        CONF_POLL_INTERVAL: 5,
    }


class AuthFailingRepository:
    """Repository that fails with an authentication error."""

    async def read_all(self) -> list[Period]:
        raise ServiceAccountAccessTokenError({"error": "invalid_grant"})

    async def upsert(self, period: Period) -> None:
        pass

    async def delete(self, period_id: UUID) -> None:
        pass


class EmptyRepository:
    """Repository with no periods."""

    async def read_all(self) -> list[Period]:
        return []

    async def upsert(self, period: Period) -> None:
        pass

    async def delete(self, period_id: UUID) -> None:
        pass


@pytest.fixture
def cache_store(hass: HomeAssistant) -> Store[dict[str, Any]]:
    """Return an isolated in-memory cache store."""
    return Store(hass, 1, "test_sync_cache_repairs")


@pytest.fixture
def sheet_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry with sheet settings."""
    key_path = "/config/cycle_tracker_service_account.json"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_sheet_entry_data(key_path),
        title="Cycle Tracker",
    )
    entry.add_to_hass(hass)
    return entry


async def test_auth_failure_creates_sheet_auth_failed_issue(
    hass: HomeAssistant,
    sheet_config_entry: MockConfigEntry,
    cache_store: Store[dict[str, Any]],
) -> None:
    """A token-exchange failure creates the sheet_auth_failed repair issue."""
    coordinator = CycleTrackerCoordinator(
        hass,
        sheet_config_entry,
        repo=AuthFailingRepository(),
        cache_store=cache_store,
    )

    await coordinator.async_refresh()

    registry = async_get(hass)
    issue = registry.async_get_issue(DOMAIN, ISSUE_SHEET_AUTH_FAILED)
    assert issue is not None
    assert issue.active is True


async def test_later_success_clears_sheet_auth_failed_issue(
    hass: HomeAssistant,
    sheet_config_entry: MockConfigEntry,
    cache_store: Store[dict[str, Any]],
) -> None:
    """A successful read after a failure clears the auth issue."""
    failing = CycleTrackerCoordinator(
        hass,
        sheet_config_entry,
        repo=AuthFailingRepository(),
        cache_store=cache_store,
    )
    await failing.async_refresh()
    registry = async_get(hass)
    assert registry.async_get_issue(DOMAIN, ISSUE_SHEET_AUTH_FAILED) is not None

    succeeding = CycleTrackerCoordinator(
        hass,
        sheet_config_entry,
        repo=EmptyRepository(),
        cache_store=cache_store,
    )
    await succeeding.async_refresh()

    assert registry.async_get_issue(DOMAIN, ISSUE_SHEET_AUTH_FAILED) is None


async def test_invalid_rows_create_sheet_rows_invalid_issue(
    hass: HomeAssistant,
    sheet_config_entry: MockConfigEntry,
    cache_store: Store[dict[str, Any]],
) -> None:
    """A successful Sheets read with invalid rows creates sheet_rows_invalid."""
    from custom_components.cycle_tracker.repository import SheetsPeriodRepository
    from custom_components.cycle_tracker.sheets import SheetsClient

    client = AsyncMock(spec=SheetsClient)
    client.read_rows.return_value = [
        [
            "period_id",
            "start_date",
            "end_date",
            "flow_intensity",
            "notes",
            "updated_at",
        ],
        ["", "", "", "", "", ""],  # invalid: missing start date
    ]
    repo = SheetsPeriodRepository(
        client,
        sheet_config_entry.data[CONF_SPREADSHEET_ID],
        sheet_config_entry.data[CONF_WORKSHEET],
    )

    coordinator = CycleTrackerCoordinator(
        hass,
        sheet_config_entry,
        repo=repo,
        cache_store=cache_store,
    )

    await coordinator.async_refresh()

    assert repo.last_invalid_reports
    registry = async_get(hass)
    issue = registry.async_get_issue(DOMAIN, ISSUE_SHEET_ROWS_INVALID)
    assert issue is not None
    assert issue.active is True


async def test_not_configured_entry_creates_sheet_not_configured_issue(
    hass: HomeAssistant,
) -> None:
    """An entry without sheet settings creates the sheet_not_configured issue."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "cycle_length": 28,
            "period_length": 5,
            "last_period_start": "2026-01-01",
            "prediction_algorithm": "weighted_moving_average",
        },
    )
    entry.add_to_hass(hass)
    coordinator = CycleTrackerCoordinator(hass, entry)

    await coordinator.async_refresh()

    registry = async_get(hass)
    issue = registry.async_get_issue(DOMAIN, "sheet_not_configured")
    assert issue is not None
    assert issue.active is True
