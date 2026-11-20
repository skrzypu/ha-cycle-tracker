"""Refresh button for Cycle Tracker."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SERVICE_REFRESH
from .coordinator import CycleTrackerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Cycle Tracker refresh button."""
    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RefreshButton(coordinator, entry)])


class RefreshButton(CoordinatorEntity[CycleTrackerCoordinator], ButtonEntity):
    """Button that requests an immediate re-read of the configured sheet."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the refresh button."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Cycle Tracker Refresh"
        self._attr_unique_id = f"{entry.entry_id}_refresh"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Cycle Tracker",
            "manufacturer": "Cycle Tracker",
            "model": "Menstrual Cycle Tracker",
        }
        self._attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        """Request a refresh through the service, targeting this button."""
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH,
            target={"entity_id": self.entity_id},
            blocking=True,
        )
