"""Tests for the bundled Lovelace dashboard."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker import dashboard as dashboard_module
from custom_components.cycle_tracker.const import DOMAIN
from custom_components.cycle_tracker.dashboard import (
    DASHBOARD_URL_PATH,
    DASHBOARD_VIEW,
    async_ensure_dashboard,
    async_remove_dashboard,
)

CREATE = "lovelace/dashboards/create"
DELETE = "lovelace/dashboards/delete"


class FakeDashboard:
    """In-memory stand-in for a LovelaceStorage dashboard config."""

    def __init__(
        self, config: dict[str, Any] | None = None, mode: str = "auto-gen"
    ) -> None:
        """Store the initial config and reporting mode."""
        self._config = config
        self.mode = mode
        self.saved: list[dict[str, Any]] = []
        self.loaded: list[bool] = []
        self.config = {
            "id": DASHBOARD_URL_PATH,
            "url_path": DASHBOARD_URL_PATH,
            "title": "Cykl",
            "mode": "storage",
        }

    async def async_get_info(self) -> dict[str, str]:
        """Report whether a config has been saved yet."""
        return {"mode": self.mode}

    async def async_save(self, config: dict[str, Any]) -> None:
        """Record a saved config."""
        self.saved.append(config)
        self._config = config
        self.mode = "storage"

    async def async_load(self, force: bool = False) -> dict[str, Any] | None:
        """Return the current config."""
        self.loaded.append(force)
        return self._config


class FakeMarkerStore:
    """In-memory stand-in for the ownership-marker Store."""

    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        """Start with an optional persisted payload."""
        self.payload: dict[str, Any] = dict(payload or {})
        self.saves: list[dict[str, Any]] = []

    async def async_load(self) -> dict[str, Any]:
        """Return the persisted payload."""
        return dict(self.payload)

    async def async_save(self, payload: dict[str, Any]) -> None:
        """Record a new payload."""
        self.saves.append(dict(payload))
        self.payload = dict(payload)


class FakeWS:
    """Collect calls made to the dashboard websocket commands."""

    def __init__(self) -> None:
        """Start with empty call logs."""
        self.created: list[dict[str, Any]] = []
        self.deleted: list[str] = []

    async def create(
        self, hass: HomeAssistant, connection: Any, msg: dict[str, Any]
    ) -> None:
        """Create the dashboard in the fake Lovelace data."""
        self.created.append({key: value for key, value in msg.items() if key != "id"})
        hass.data["lovelace"].dashboards[msg["url_path"]] = FakeDashboard()
        connection.send_result(msg["id"], {"id": DASHBOARD_URL_PATH})

    async def delete(
        self, hass: HomeAssistant, connection: Any, msg: dict[str, Any]
    ) -> None:
        """Delete the dashboard from the fake Lovelace data."""
        self.deleted.append(msg["dashboard_id"])
        hass.data["lovelace"].dashboards.pop(DASHBOARD_URL_PATH, None)
        connection.send_result(msg["id"])


def test_seeded_view_still_uses_the_single_existing_card_element() -> None:
    """The bundled view seeds one card, not a second card for the new average."""
    cards = DASHBOARD_VIEW["views"][0]["cards"]

    assert len(cards) == 1
    assert cards[0]["type"] == "custom:cycle-tracker-card"


@pytest.fixture
def env(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Install fake Lovelace, websocket and marker stores, then restore them."""
    keys = ("lovelace", "websocket_api", "frontend_panels")
    saved = {key: hass.data.get(key) for key in keys}
    ws = FakeWS()
    dashboards: dict[str, FakeDashboard] = {}
    marker = FakeMarkerStore()
    hass.data["lovelace"] = SimpleNamespace(dashboards=dashboards)
    hass.data["websocket_api"] = {
        CREATE: (ws.create, None),
        DELETE: (ws.delete, None),
    }
    monkeypatch.setattr(dashboard_module, "_marker_store", lambda hass: marker)
    yield SimpleNamespace(ws=ws, dashboards=dashboards, marker=marker)
    for key, value in saved.items():
        if value is None:
            hass.data.pop(key, None)
        else:
            hass.data[key] = value


async def test_first_setup_creates_and_seeds_dashboard(
    hass: HomeAssistant, env: Any
) -> None:
    """The first setup creates the dashboard once and seeds the card view."""
    assert await async_ensure_dashboard(hass) is True

    assert len(env.ws.created) == 1
    assert env.ws.created[0]["url_path"] == DASHBOARD_URL_PATH
    assert env.ws.created[0]["show_in_sidebar"] is True
    assert env.marker.payload == {"created": True, "seeded": DASHBOARD_VIEW}
    assert env.dashboards[DASHBOARD_URL_PATH].saved == [DASHBOARD_VIEW]

    await async_ensure_dashboard(hass)

    assert len(env.ws.created) == 1


async def test_existing_dashboard_without_marker_is_untouched(
    hass: HomeAssistant, env: Any
) -> None:
    """A dashboard the integration did not create is never seeded or changed."""
    existing = FakeDashboard(config={"views": [{"title": "Mine"}]}, mode="storage")
    env.dashboards[DASHBOARD_URL_PATH] = existing

    assert await async_ensure_dashboard(hass) is True

    assert env.ws.created == []
    assert existing.saved == []
    assert env.marker.saves == []


async def test_panel_name_conflict_is_left_alone(hass: HomeAssistant, env: Any) -> None:
    """An existing panel with the same URL path prevents creation."""
    hass.data["frontend_panels"] = {DASHBOARD_URL_PATH: object()}

    assert await async_ensure_dashboard(hass) is True

    assert env.ws.created == []


async def test_deleted_dashboard_is_not_recreated(
    hass: HomeAssistant, env: Any
) -> None:
    """A dashboard the user deleted is not brought back on a later setup."""
    env.marker.payload = {"created": True}

    assert await async_ensure_dashboard(hass) is True

    assert env.ws.created == []


async def test_edited_dashboard_is_kept_on_removal(
    hass: HomeAssistant, env: Any
) -> None:
    """Removing the integration keeps a dashboard the user customised."""
    env.marker.payload = {"created": True}
    env.dashboards[DASHBOARD_URL_PATH] = FakeDashboard(
        config={"views": [{"title": "Edited"}]}, mode="storage"
    )

    await async_remove_dashboard(hass)

    assert env.ws.deleted == []
    assert env.marker.payload == {"created": True}


async def test_unmodified_dashboard_is_removed(hass: HomeAssistant, env: Any) -> None:
    """An unmodified dashboard is deleted along with its ownership marker."""
    env.marker.payload = {"created": True}
    env.dashboards[DASHBOARD_URL_PATH] = FakeDashboard(
        config=DASHBOARD_VIEW, mode="storage"
    )

    await async_remove_dashboard(hass)

    assert env.ws.deleted == [DASHBOARD_URL_PATH]
    assert env.marker.payload == {}


async def test_returns_false_when_lovelace_data_missing(
    hass: HomeAssistant, env: Any
) -> None:
    """Missing Lovelace data is reported so the caller can retry."""
    hass.data.pop("lovelace")

    assert await async_ensure_dashboard(hass) is False


async def test_returns_false_when_create_command_unregistered(
    hass: HomeAssistant, env: Any
) -> None:
    """A missing websocket handler is reported so the caller can retry."""
    hass.data["websocket_api"] = {}

    assert await async_ensure_dashboard(hass) is False


async def test_handler_failure_is_contained(
    hass: HomeAssistant, env: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """A failing websocket command is logged, never raised into setup."""

    async def boom(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
        raise RuntimeError("websockets down")

    hass.data["websocket_api"][CREATE] = (boom, None)

    assert await async_ensure_dashboard(hass) is True
    assert "could not manage the dashboard" in caplog.text


async def test_multi_person_dashboard_seeds_one_bound_card_per_device(
    hass: HomeAssistant, env: Any
) -> None:
    """A household with two entries gets two cards, each bound by device_id."""
    registry = dr.async_get(hass)
    devices = []
    for name in ("Anna", "Beata"):
        entry = MockConfigEntry(domain=DOMAIN, title=name)
        entry.add_to_hass(hass)
        devices.append(
            registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, entry.entry_id)},
                name=name,
            )
        )

    assert await async_ensure_dashboard(hass) is True

    saved = env.dashboards[DASHBOARD_URL_PATH].saved
    assert len(saved) == 1
    cards = saved[0]["views"][0]["cards"]
    assert len(cards) == 2
    assert [card["device_id"] for card in cards] == [
        devices[0].id,
        devices[1].id,
    ]
    assert [card["title"] for card in cards] == ["Anna", "Beata"]
    assert env.marker.payload["seeded"] == saved[0]


async def test_seeded_view_is_compared_on_removal(
    hass: HomeAssistant, env: Any
) -> None:
    """Removal compares the dashboard with the view that was actually seeded."""
    seeded = {"views": [{"title": "Cykl", "cards": []}]}
    env.marker.payload = {"created": True, "seeded": seeded}
    env.dashboards[DASHBOARD_URL_PATH] = FakeDashboard(config=seeded, mode="storage")

    await async_remove_dashboard(hass)

    assert env.ws.deleted == [DASHBOARD_URL_PATH]
