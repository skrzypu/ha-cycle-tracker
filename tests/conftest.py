"""Home Assistant fixtures shared by the adapter and end-to-end suites.

The domain tests keep their own conftest: they deliberately stay free of the
Home Assistant harness (ADR-0005), so nothing here imports Home Assistant at
module scope. ``config_entry`` is the single entry both suites build on, which
keeps the settings they exercise from drifting apart, and ``coordinator``
remains the adapter-level handle while the end-to-end tests go through the
service registry instead.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator

# `pytest_homeassistant_custom_component` is registered through its `pytest11`
# entry point, so the Home Assistant fixtures are already available here; pytest
# rejects a `pytest_plugins` declaration outside the rootdir conftest.

FROZEN_TODAY = date(2026, 11, 13)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request: pytest.FixtureRequest) -> Iterator[None]:
    """Let Home Assistant load the custom integration under test.

    Only tests that use ``hass`` opt in, so the framework-free domain tests keep
    running without requesting a Home Assistant fixture.
    """
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")
    yield


@pytest.fixture
def frozen_today(freezer) -> date:
    """Pin the wall clock so the snapshot reference date is deterministic."""
    freezer.move_to("2026-11-13 12:00:00")
    return FROZEN_TODAY


@pytest.fixture
def service_account_key(hass: HomeAssistant) -> str:
    """Generate and write a throwaway service-account key file.

    The key is written inside ``hass.config.config_dir`` so relative paths in
    config entries resolve to it. The filename is returned so tests can reuse
    the same value in entry data.
    """
    import json
    from pathlib import Path

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    info = {
        "type": "service_account",
        "client_email": "test@example.iam.gserviceaccount.com",
        "private_key": pem,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    key_path = Path(hass.config.config_dir) / "service_account.json"
    key_path.write_text(json.dumps(info), encoding="utf-8")
    return "service_account.json"


@pytest.fixture
def sheet_settings(service_account_key: str) -> dict[str, Any]:
    """Return the Google Sheets settings of the shared entry.

    Tests that override ``config_entry_data`` spread this mapping into their
    own dict so a changed entry stays sheet-backed instead of silently losing
    the sheet settings and running unconfigured.
    """
    from custom_components.cycle_tracker.const import (
        CONF_POLL_INTERVAL,
        CONF_SERVICE_ACCOUNT_FILE,
        CONF_SPREADSHEET_ID,
        CONF_WORKSHEET,
    )

    return {
        CONF_SPREADSHEET_ID: "test-sheet-id",
        CONF_WORKSHEET: "Sheet1",
        CONF_SERVICE_ACCOUNT_FILE: service_account_key,
        CONF_POLL_INTERVAL: 5,
    }


@pytest.fixture
def config_entry_data(sheet_settings: dict[str, Any]) -> dict[str, Any]:
    """Return the settings of the shared entry.

    A test module can override this fixture to exercise an entry with different
    or missing settings, which is how the shipped defaults get covered. Such an
    override spreads in ``sheet_settings`` unless it deliberately tests an
    unconfigured entry.
    """
    from custom_components.cycle_tracker.const import (
        CONF_CYCLE_LENGTH,
        CONF_LAST_PERIOD_START,
        CONF_PERIOD_LENGTH,
        CONF_PREDICTION_ALGORITHM,
    )

    return {
        CONF_CYCLE_LENGTH: 28,
        CONF_PERIOD_LENGTH: 5,
        CONF_LAST_PERIOD_START: "2026-01-01",
        CONF_PREDICTION_ALGORITHM: "weighted_moving_average",
        **sheet_settings,
    }


@pytest.fixture
def sheet_emulator(hass: HomeAssistant, aioclient_mock: Any, service_account_key: str):
    """Return an in-memory Google Sheet emulator wired to ``aioclient_mock``.

    The emulator registers handlers for the OAuth2 token endpoint and the four
    Sheets API operations used by the integration: read, append, update and
    clear. Tests can pre-seed rows with ``seed(rows)`` and inspect the current
    data rows via ``rows``. The grid persists for the whole test, so an unload
    followed by a fresh setup re-reads the same rows.
    """
    import re

    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMockResponse,
    )

    HEADER = [
        "period_id",
        "start_date",
        "end_date",
        "flow_intensity",
        "notes",
        "updated_at",
    ]

    class SheetEmulator:
        """Mutable sheet grid backed by ``aioclient_mock`` side effects."""

        def __init__(self, mocker) -> None:
            self._mocker = mocker
            self._rows: list[list[Any]] = []
            self._register()

        @property
        def rows(self) -> list[list[Any]]:
            """Return a copy of the current data rows (header excluded)."""
            return [list(row) for row in self._rows]

        def seed(self, rows: list[list[Any]]) -> None:
            """Replace the data rows with ``rows``."""
            self._rows = [list(row) for row in rows]

        def _register(self) -> None:
            self._mocker.post(
                "https://oauth2.googleapis.com/token",
                status=200,
                json={
                    "access_token": "TOKEN",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
            self._mocker.get(
                re.compile(
                    r"https://sheets\.googleapis\.com/v4/spreadsheets/[^/]+/values/[^/]+"
                ),
                side_effect=self._handle_get,
            )
            self._mocker.post(
                re.compile(r":append"),
                side_effect=self._handle_append,
            )
            self._mocker.put(
                # The regex is matched against the whole URL, query string
                # included, so the range is anchored on the ``?`` that follows
                # ``valueInputOption`` rather than on the end of the string.
                re.compile(
                    r"https://sheets\.googleapis\.com/v4/spreadsheets/[^/]+/values/[^/]+![A-Z]+\d+:[A-Z]+\d+\?"
                ),
                side_effect=self._handle_update,
            )
            self._mocker.post(
                re.compile(r":clear"),
                side_effect=self._handle_clear,
            )

        async def _handle_get(self, method, url, data):
            return AiohttpClientMockResponse(
                method=method,
                url=url,
                status=200,
                json={"values": [HEADER, *self._rows]},
            )

        async def _handle_append(self, method, url, data):
            row = data["values"][0]
            self._rows.append(row)
            return AiohttpClientMockResponse(
                method=method, url=url, status=200, json={}
            )

        async def _handle_update(self, method, url, data):
            row = data["values"][0]
            match = re.search(r"![A-Z]+(\d+):[A-Z]+\d+", str(url))
            if match:
                row_index = int(match.group(1)) - 2  # header is row 1
                while len(self._rows) <= row_index:
                    self._rows.append(["", "", "", "", "", ""])
                self._rows[row_index] = row
            return AiohttpClientMockResponse(
                method=method, url=url, status=200, json={}
            )

        async def _handle_clear(self, method, url, data):
            match = re.search(r"![A-Z]+(\d+):[A-Z]+\d+:clear", str(url))
            if match:
                row_index = int(match.group(1)) - 2
                if 0 <= row_index < len(self._rows):
                    self._rows[row_index] = ["", "", "", "", "", ""]
            return AiohttpClientMockResponse(
                method=method, url=url, status=200, json={}
            )

    return SheetEmulator(aioclient_mock)


@pytest.fixture
def config_entry(
    hass: HomeAssistant,
    config_entry_data: dict[str, Any],
    sheet_emulator: Any,
) -> MockConfigEntry:
    """Return a registered config entry carrying ``config_entry_data``.

    The entry depends on ``sheet_emulator`` so the Google Sheets mock is always
    in place before a configured entry is set up.
    """
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.cycle_tracker.const import DOMAIN

    entry = MockConfigEntry(domain=DOMAIN, data=config_entry_data)
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def coordinator(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    frozen_today: date,
) -> AsyncIterator[CycleTrackerCoordinator]:
    """Set up the integration and return its coordinator."""
    from custom_components.cycle_tracker.const import DOMAIN

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    yield coordinator

    await coordinator.async_shutdown()
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
def period_row() -> Callable[..., dict[str, Any]]:
    """Return a helper that builds a stored period row with a stable id."""

    def _period_row(
        start: date,
        length: int = 5,
        flow: str = "medium",
        notes: str | None = None,
        updated_at: str | None = None,
        period_id: str | None = None,
    ) -> dict[str, Any]:
        if period_id is None:
            from custom_components.cycle_tracker.domain.models import legacy_period_id

            period_id = str(legacy_period_id(start))
        return {
            "period_id": period_id,
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=length - 1)).isoformat(),
            "flow_intensity": flow,
            "notes": notes,
            "updated_at": updated_at,
        }

    return _period_row
