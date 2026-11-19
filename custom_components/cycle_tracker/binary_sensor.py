"""Binary sensor for whether a period is open."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CycleTrackerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Cycle Tracker period-open binary sensor."""
    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PeriodOpenBinarySensor(coordinator, entry)])


class PeriodOpenBinarySensor(
    CoordinatorEntity[CycleTrackerCoordinator], BinarySensorEntity
):
    """Binary sensor that reports whether a recorded period is open."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Cycle Tracker Period Open"
        self._attr_unique_id = f"{entry.entry_id}_period_open"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Cycle Tracker",
            "manufacturer": "Cycle Tracker",
            "model": "Menstrual Cycle Tracker",
        }
        self._attr_icon = "mdi:water"

    @property
    def available(self) -> bool:
        """Mirror the coordinator's availability state."""
        return self.coordinator.available

    @property
    def is_on(self) -> bool:
        """Return True while a recorded period is open."""
        return self.coordinator.snapshot.period_open
