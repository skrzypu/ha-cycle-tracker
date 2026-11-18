"""Services for Cycle Tracker.

The services are domain-level, not per config entry, so a call has to say which
entry it means. That is resolved from the call's target — an entity, device or
area of this integration — through the entity registry, falling back to the only
configured entry when the call carries no target. Because
``ServiceRegistry.async_call`` merges the target into the service data before
validating, both schemas also accept the target keys.
"""

from typing import Any

import voluptuous as vol
from homeassistant.const import ATTR_AREA_ID, ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import async_extract_entity_ids

from .const import (
    DOMAIN,
    SERVICE_LOG_END,
    SERVICE_LOG_START,
)
from .coordinator import CycleTrackerCoordinator

#: Target keys the service registry injects into the call data. The handlers
#: read the selection through ``async_extract_entity_ids``, not from these keys.
_TARGET_FIELDS: dict[Any, Any] = {
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [str]),
    vol.Optional(ATTR_AREA_ID): vol.All(cv.ensure_list, [str]),
}

SERVICE_LOG_START_SCHEMA = vol.Schema(
    {
        vol.Required("date"): cv.date,
        vol.Optional("flow_intensity", default="medium"): vol.In(
            ["spotting", "light", "medium", "heavy"]
        ),
        **_TARGET_FIELDS,
    }
)

SERVICE_LOG_END_SCHEMA = vol.Schema(
    {
        vol.Required("date"): cv.date,
        **_TARGET_FIELDS,
    }
)


async def _async_resolve_coordinator(
    hass: HomeAssistant, call: ServiceCall
) -> CycleTrackerCoordinator:
    """Resolve the coordinator a call applies to, or reject the call."""
    coordinators: dict[str, CycleTrackerCoordinator] = hass.data.get(DOMAIN, {})
    entity_ids = await async_extract_entity_ids(call)

    if not entity_ids:
        if len(coordinators) == 1:
            return next(iter(coordinators.values()))
        raise ServiceValidationError(
            "Cycle Tracker cannot tell which data to update. Target an entity of "
            f"the {DOMAIN} integration, or set up exactly one Cycle Tracker entry."
        )

    registry = er.async_get(hass)
    entry_ids: set[str] = set()
    for entity_id in entity_ids:
        entity_entry = registry.async_get(entity_id)
        if entity_entry is None or entity_entry.config_entry_id is None:
            continue
        if entity_entry.config_entry_id in coordinators:
            entry_ids.add(entity_entry.config_entry_id)

    if not entry_ids:
        raise ServiceValidationError(
            "None of the targeted entities belong to Cycle Tracker."
        )
    if len(entry_ids) > 1:
        raise ServiceValidationError(
            "The target spans several Cycle Tracker entries. Target an entity of a "
            "single entry, or call the service once per entry."
        )
    return coordinators[entry_ids.pop()]


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Cycle Tracker."""

    async def handle_log_start(call: ServiceCall) -> ServiceResponse:
        """Handle log_start service call."""
        coordinator = await _async_resolve_coordinator(hass, call)
        start = call.data["date"]
        flow_intensity = call.data["flow_intensity"]

        await coordinator.async_log_start(start, flow_intensity)
        coordinator.async_set_updated_data(coordinator._data)

        return {
            "success": True,
            "message": f"Period start logged for {start.isoformat()}",
        }

    async def handle_log_end(call: ServiceCall) -> ServiceResponse:
        """Handle log_end service call."""
        coordinator = await _async_resolve_coordinator(hass, call)
        end = call.data["date"]

        result = await coordinator.async_log_end(end)
        if result["success"]:
            coordinator.async_set_updated_data(coordinator._data)
        return result

    hass.services.async_register(
        DOMAIN,
        SERVICE_LOG_START,
        handle_log_start,
        schema=SERVICE_LOG_START_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_LOG_END,
        handle_log_end,
        schema=SERVICE_LOG_END_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, SERVICE_LOG_START)
    hass.services.async_remove(DOMAIN, SERVICE_LOG_END)
