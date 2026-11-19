"""Cycle Tracker integration for Home Assistant."""

from __future__ import annotations

import logging
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any, Protocol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import DOMAIN, PLATFORMS
from .coordinator import CycleTrackerCoordinator
from .dashboard import async_ensure_dashboard, async_remove_dashboard
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

#: URL path the card asset is served under.
CARD_URL_PATH = "/cycle_tracker/cycle-tracker-card.js"

_STATIC_PATH_REGISTERED = False
_LOVELACE_WIRED = False

#: ``hass.data`` marker guarding against scheduling more than one retry.
_LOVELACE_RETRY_DATA_KEY = f"{DOMAIN}_lovelace_retry_scheduled"
#: ``hass.data`` marker guarding the single dashboard retry.
_DASHBOARD_RETRY_DATA_KEY = f"{DOMAIN}_dashboard_retry_scheduled"
#: Delay before the single retry when Lovelace is not ready yet.
_LOVELACE_RETRY_DELAY = 10


class _ResourceCollection(Protocol):
    """The subset of the Lovelace resources collection this integration uses."""

    async def async_load(self) -> None: ...

    def async_items(self) -> list[dict[str, Any]]: ...

    async def async_create_item(self, data: dict[str, Any]) -> Any: ...

    async def async_update_item(self, item_id: str, updates: dict[str, Any]) -> Any: ...

    async def async_delete_item(self, item_id: str) -> None: ...


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the card asset and wire the Lovelace resource once per process."""
    await _async_register_card_static_path(hass)
    _wire_lovelace_resource(hass)
    await _async_wire_dashboard(hass)
    return True


async def _async_register_card_static_path(hass: HomeAssistant) -> None:
    """Register the card asset as a static path, exactly once."""
    global _STATIC_PATH_REGISTERED
    if _STATIC_PATH_REGISTERED:
        return
    _STATIC_PATH_REGISTERED = True
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path=CARD_URL_PATH,
                path=str(Path(__file__).parent / "www" / "cycle-tracker-card.js"),
                cache_headers=True,
            )
        ]
    )


def _wire_lovelace_resource(hass: HomeAssistant) -> None:
    """Schedule the Lovelace resource upsert, exactly once per process."""
    global _LOVELACE_WIRED
    if _LOVELACE_WIRED:
        return
    _LOVELACE_WIRED = True

    async def _on_started(_: Event) -> None:
        await _async_upsert_lovelace_resource(hass)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)
    if hass.is_running:
        hass.async_create_task(_async_upsert_lovelace_resource(hass))


def _lovelace_resources_collection(
    hass: HomeAssistant,
) -> _ResourceCollection | None:
    """Return the Lovelace resources collection, or None when unusable."""
    lovelace_data = hass.data.get("lovelace")
    if lovelace_data is None:
        _LOGGER.info("Cycle Tracker: Lovelace data missing")
        return None
    # Home Assistant 2026.11 renamed ``LovelaceData.mode`` to ``resource_mode``;
    # reading the old attribute alone yields ``None`` and silently skips wiring.
    mode = getattr(lovelace_data, "resource_mode", None)
    if mode is None:
        mode = getattr(lovelace_data, "mode", None)
    if mode != "storage":
        _LOGGER.info(
            "Cycle Tracker: Lovelace is not in storage mode (mode=%s); "
            "skipping card resource management",
            mode,
        )
        return None
    collection = getattr(lovelace_data, "resources", None)
    if collection is None:
        _LOGGER.info(
            "Cycle Tracker: Lovelace resources collection missing (mode=%s)", mode
        )
        return None
    return collection


def _is_card_resource(url: str) -> bool:
    """Return True when a resource URL points at the card asset."""
    return url.startswith(CARD_URL_PATH)


async def _card_resource_url(hass: HomeAssistant) -> str:
    """Return the versioned card asset URL from the manifest version."""
    integration = await async_get_integration(hass, DOMAIN)
    manifest_version = integration.version
    version = str(manifest_version) if manifest_version is not None else ""
    return f"{CARD_URL_PATH}?v={version}"


async def _async_upsert_lovelace_resource(hass: HomeAssistant) -> bool:
    """Create or update the Lovelace resource for the card asset.

    Returns ``False`` only when the resources collection is unavailable, so a
    caller can retry later. Never raises: failures in the background task are
    logged instead of surfacing to the task that scheduled it.
    """
    try:
        collection = _lovelace_resources_collection(hass)
        if collection is None:
            return False

        target_url = await _card_resource_url(hass)

        await collection.async_load()
        for item in collection.async_items():
            if not _is_card_resource(item.get("url", "")):
                continue
            if item["url"] == target_url:
                _LOGGER.info(
                    "Cycle Tracker: Lovelace resource already present: %s",
                    target_url,
                )
                return True
            _LOGGER.info(
                "Cycle Tracker: updating Lovelace resource %s -> %s",
                item["url"],
                target_url,
            )
            await collection.async_update_item(
                item["id"], {"res_type": "module", "url": target_url}
            )
            return True

        _LOGGER.info("Cycle Tracker: creating Lovelace resource %s", target_url)
        await collection.async_create_item({"res_type": "module", "url": target_url})
    except Exception:
        _LOGGER.warning(
            "Cycle Tracker: could not manage the Lovelace resource",
            exc_info=True,
        )
    return True


async def _async_remove_lovelace_resource(hass: HomeAssistant) -> None:
    """Delete the card asset resource when it exists."""
    try:
        collection = _lovelace_resources_collection(hass)
        if collection is None:
            return

        await collection.async_load()
        for item in collection.async_items():
            if _is_card_resource(item.get("url", "")):
                await collection.async_delete_item(item["id"])
                return
    except Exception:
        _LOGGER.warning(
            "Cycle Tracker: could not remove the Lovelace resource",
            exc_info=True,
        )


def _schedule_lovelace_resource_retry(hass: HomeAssistant) -> None:
    """Retry the upsert once, shortly after the entry was set up.

    A delayed single retry is simpler than waiting for
    ``EVENT_HOMEASSISTANT_STARTED``: an entry added at runtime never sees a new
    started event, and this works during startup too. The guard keeps the number
    of pending retries bounded.
    """
    if hass.data.get(_LOVELACE_RETRY_DATA_KEY):
        return
    hass.data[_LOVELACE_RETRY_DATA_KEY] = True

    async def _retry(_now: datetime) -> None:
        hass.data.pop(_LOVELACE_RETRY_DATA_KEY, None)
        await _async_upsert_lovelace_resource(hass)

    async_call_later(hass, _LOVELACE_RETRY_DELAY, _retry)


async def _async_wire_dashboard(hass: HomeAssistant) -> None:
    """Create the bundled dashboard, retrying once when Lovelace is not ready."""
    try:
        ready = await async_ensure_dashboard(hass)
    except Exception:
        _LOGGER.warning(
            "Cycle Tracker: could not manage the dashboard",
            exc_info=True,
        )
        return
    if not ready:
        _schedule_dashboard_retry(hass)


def _schedule_dashboard_retry(hass: HomeAssistant) -> None:
    """Retry the dashboard creation once, ten seconds later.

    The ``hass.data`` marker stays set for the duration of the retry, so the
    retry cannot schedule another one: at most a single retry is ever pending.
    """
    if hass.data.get(_DASHBOARD_RETRY_DATA_KEY):
        return
    hass.data[_DASHBOARD_RETRY_DATA_KEY] = True

    async def _retry(_now: datetime) -> None:
        try:
            await _async_wire_dashboard(hass)
        finally:
            hass.data.pop(_DASHBOARD_RETRY_DATA_KEY, None)

    async_call_later(hass, _LOVELACE_RETRY_DELAY, _retry)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cycle Tracker from a config entry."""
    coordinator = CycleTrackerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # A runtime-added entry never sees the original start event, so attempt the
    # Lovelace resource here as well; the upsert is idempotent.
    if not await _async_upsert_lovelace_resource(hass):
        _schedule_lovelace_resource_retry(hass)

    await _async_wire_dashboard(hass)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Set up services and remove them again when the entry unloads
    await async_setup_services(hass)
    entry.async_on_unload(partial(async_unload_services, hass))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: CycleTrackerCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the Lovelace resource and dashboard once the last entry is gone."""
    remaining = [
        item
        for item in hass.config_entries.async_entries(DOMAIN)
        if item.entry_id != entry.entry_id
    ]
    if remaining:
        return
    await _async_remove_lovelace_resource(hass)
    try:
        await async_remove_dashboard(hass)
    except Exception:
        _LOGGER.warning(
            "Cycle Tracker: could not manage the dashboard",
            exc_info=True,
        )


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry after its options changed.

    The manager reload also drives the entry through ``SETUP_IN_PROGRESS``,
    which ``async_config_entry_first_refresh`` requires; calling the component's
    unload and setup directly leaves the entry ``LOADED`` and the refresh fails.
    """
    await hass.config_entries.async_reload(entry.entry_id)
