"""Bundled Lovelace dashboard for the Cycle Tracker integration.

Home Assistant has no public API to create a storage dashboard, so this module
drives the frontend's own websocket commands (``lovelace/dashboards/create`` and
``.../delete``) through a stub connection. A small marker store records that the
dashboard was created here, which keeps the integration from touching a
dashboard the user built or deleted themselves.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from types import SimpleNamespace
from typing import Any

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

#: URL path of the bundled dashboard; it must contain a hyphen.
DASHBOARD_URL_PATH = "cykl-miesieczny"
DASHBOARD_TITLE = "Cykl"
DASHBOARD_ICON = "mdi:calendar-heart"
#: The view seeded when no device exists yet (or the registry is unavailable).
DASHBOARD_VIEW: dict[str, Any] = {
    "views": [
        {
            "title": "Cykl",
            "path": "cykl",
            "icon": DASHBOARD_ICON,
            "cards": [{"type": "custom:cycle-tracker-card"}],
        }
    ]
}


def _dashboard_view(hass: HomeAssistant) -> dict[str, Any]:
    """Build the seeded view: one card per Cycle Tracker device.

    A household can run the integration once per person, so the bundled
    dashboard must not assume a single one. Each card is bound by ``device_id``
    — never by an entity ID — and a multi-person dashboard titles every card
    with the device name. The order is deterministic (device name, then id), so
    two setups with the same devices seed the same view.
    """
    registry = dr.async_get(hass)
    devices = [
        device
        for device in registry.devices.values()
        if any(identifier[0] == DOMAIN for identifier in device.identifiers)
    ]
    if not devices:
        return DASHBOARD_VIEW

    devices.sort(key=lambda device: ((device.name_by_user or device.name or ""), device.id))
    multi = len(devices) > 1
    cards: list[dict[str, Any]] = []
    for device in devices:
        card: dict[str, Any] = {
            "type": "custom:cycle-tracker-card",
            "device_id": device.id,
        }
        if multi:
            card["title"] = device.name_by_user or device.name or DASHBOARD_TITLE
        else:
            card["title"] = DASHBOARD_TITLE
        cards.append(card)

    return {
        "views": [
            {
                "title": "Cykl",
                "path": "cykl",
                "icon": DASHBOARD_ICON,
                "cards": cards,
            }
        ]
    }

_CREATE_COMMAND = "lovelace/dashboards/create"
_DELETE_COMMAND = "lovelace/dashboards/delete"

#: Seconds to wait for the websocket handler to answer.
_WS_TIMEOUT = 10


class _StubConnection:
    """Minimal stand-in for ``websocket_api.ActiveConnection``.

    The collection handlers only touch ``user``, ``subscriptions``,
    ``send_result``, ``send_error`` and ``async_handle_exception``.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.user = SimpleNamespace(is_admin=True)
        self.subscriptions: dict[int, Any] = {}
        self.future: asyncio.Future[Any] = hass.loop.create_future()

    def send_result(self, msg_id: int, result: Any = None) -> None:
        """Resolve the pending call with the handler's result."""
        if not self.future.done():
            self.future.set_result(result)

    def send_error(self, msg_id: int, code: str, message: str) -> None:
        """Reject the pending call with the handler's error."""
        if not self.future.done():
            self.future.set_exception(HomeAssistantError(f"{code}: {message}"))

    def async_handle_exception(self, msg: dict[str, Any], err: Exception) -> None:
        """Reject the pending call with the handler's exception."""
        if not self.future.done():
            self.future.set_exception(err)


async def _async_call_ws(
    hass: HomeAssistant, command: str, payload: dict[str, Any]
) -> Any:
    """Run a registered websocket command and return its result.

    Returns ``None`` when the command is not registered (yet), so a caller can
    retry later instead of failing setup.
    """
    handlers = hass.data.get("websocket_api", {})
    entry = handlers.get(command)
    if entry is None:
        return None
    handler, _schema = entry

    connection = _StubConnection(hass)
    msg = {"id": 1, "type": command, **payload}
    # Handlers wrapped by ``async_response`` are plain callbacks that schedule a
    # background task; others are coroutine functions, so support both.
    result = handler(hass, connection, msg)
    if inspect.isawaitable(result):
        await result
    return await asyncio.wait_for(connection.future, timeout=_WS_TIMEOUT)


def _marker_store(hass: HomeAssistant) -> Store[dict[str, Any]]:
    """Return the store recording that this integration created the dashboard."""
    return Store[dict[str, Any]](hass, 1, f"{DOMAIN}.dashboard")


async def _async_seed_dashboard(dashboard: Any, view: dict[str, Any]) -> bool:
    """Seed the bundled view when the dashboard still has no config."""
    try:
        info = await dashboard.async_get_info()
        if info.get("mode") != "auto-gen":
            return False
        await dashboard.async_save(view)
        _LOGGER.info("Cycle Tracker: seeded dashboard %s", DASHBOARD_URL_PATH)
        return True
    except HomeAssistantError as err:
        _LOGGER.info("Cycle Tracker: could not seed the dashboard: %s", err)
        return False


async def async_ensure_dashboard(hass: HomeAssistant) -> bool:
    """Create the bundled dashboard and seed its first view.

    Returns ``False`` when the Lovelace/websocket registries are not ready yet,
    so the caller may retry once. Never raises.
    """
    if hass.config.recovery_mode or hass.config.safe_mode:
        return True

    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return False

    handlers = hass.data.get("websocket_api", {})
    if _CREATE_COMMAND not in handlers:
        return False

    dashboards = getattr(lovelace_data, "dashboards", None)
    if dashboards is None:
        return False

    try:
        store = _marker_store(hass)
        marker = (await store.async_load()) or {}
        created_by_us = bool(marker.get("created"))

        if DASHBOARD_URL_PATH in dashboards:
            if created_by_us:
                view = _dashboard_view(hass)
                if await _async_seed_dashboard(dashboards[DASHBOARD_URL_PATH], view):
                    await store.async_save({"created": True, "seeded": view})
            _LOGGER.info(
                "Cycle Tracker: dashboard already present: %s", DASHBOARD_URL_PATH
            )
            return True

        if DASHBOARD_URL_PATH in (hass.data.get("frontend_panels") or {}):
            _LOGGER.info(
                "Cycle Tracker: a panel already uses %s; leaving it alone",
                DASHBOARD_URL_PATH,
            )
            return True

        if created_by_us:
            _LOGGER.info("Cycle Tracker: dashboard removed by the user; not recreating")
            return True

        _LOGGER.info("Cycle Tracker: creating dashboard %s", DASHBOARD_URL_PATH)
        view = _dashboard_view(hass)
        await _async_call_ws(
            hass,
            _CREATE_COMMAND,
            {
                "url_path": DASHBOARD_URL_PATH,
                "title": DASHBOARD_TITLE,
                "icon": DASHBOARD_ICON,
                "show_in_sidebar": True,
                "require_admin": False,
            },
        )

        newly_created = hass.data[LOVELACE_DATA].dashboards.get(DASHBOARD_URL_PATH)
        marker_payload: dict[str, Any] = {"created": True}
        if newly_created is not None and await _async_seed_dashboard(
            newly_created, view
        ):
            marker_payload["seeded"] = view
        await store.async_save(marker_payload)
        return True
    except Exception:
        _LOGGER.warning(
            "Cycle Tracker: could not manage the dashboard",
            exc_info=True,
        )
        return True


async def async_remove_dashboard(hass: HomeAssistant) -> None:
    """Delete the bundled dashboard, but only when the user never edited it."""
    try:
        store = _marker_store(hass)
        marker = (await store.async_load()) or {}
        if not marker.get("created"):
            return

        lovelace_data = hass.data.get(LOVELACE_DATA)
        if lovelace_data is None:
            return

        dashboard = lovelace_data.dashboards.get(DASHBOARD_URL_PATH)
        if dashboard is None:
            _LOGGER.info("Cycle Tracker: dashboard already absent; clearing the marker")
            await store.async_save({})
            return

        try:
            config = await dashboard.async_load(True)
        except HomeAssistantError as err:
            _LOGGER.info(
                "Cycle Tracker: dashboard config unavailable (%s); keeping it", err
            )
            return
        if config != (marker.get("seeded") or DASHBOARD_VIEW):
            _LOGGER.info("Cycle Tracker: dashboard was customised; keeping it")
            return

        dashboard_id = (dashboard.config or {}).get("id", DASHBOARD_URL_PATH)
        await _async_call_ws(hass, _DELETE_COMMAND, {"dashboard_id": dashboard_id})
        await store.async_save({})
    except Exception:
        _LOGGER.warning(
            "Cycle Tracker: could not manage the dashboard",
            exc_info=True,
        )
