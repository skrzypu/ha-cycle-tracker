"""Sensor entities for Cycle Tracker."""

from datetime import date
from typing import Any
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTR_CYCLE_DAY,
    ATTR_CYCLE_PHASE,
    ATTR_NEXT_PERIOD_DATE,
    ATTR_NEXT_OVULATION_DATE,
    ATTR_DAYS_UNTIL_PERIOD,
    ATTR_DAYS_UNTIL_OVULATION,
    ATTR_PREDICTION_CONFIDENCE,
    ATTR_AVERAGE_CYCLE_LENGTH,
    ATTR_AVERAGE_PERIOD_LENGTH,
    ATTR_STD_DEV_CYCLE,
    ATTR_STD_DEV_PERIOD,
    ATTR_TOTAL_CYCLES_TRACKED,
)
from .coordinator import CycleTrackerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cycle Tracker sensors."""
    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            CycleDaySensor(coordinator, entry),
            CyclePhaseSensor(coordinator, entry),
            NextPeriodDateSensor(coordinator, entry),
            NextOvulationDateSensor(coordinator, entry),
            DaysUntilPeriodSensor(coordinator, entry),
            DaysUntilOvulationSensor(coordinator, entry),
            CycleStatisticsSensor(coordinator, entry),
        ]
    )


class CycleTrackerSensor(CoordinatorEntity[CycleTrackerCoordinator], SensorEntity):
    """Base class for Cycle Tracker sensors."""

    def __init__(
        self,
        coordinator: CycleTrackerCoordinator,
        entry: ConfigEntry,
        name: str,
        unique_id_suffix: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = f"Cycle Tracker {name}"
        self._attr_unique_id = f"{entry.entry_id}_{unique_id_suffix}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Cycle Tracker",
            "manufacturer": "Cycle Tracker",
            "model": "Menstrual Cycle Tracker",
        }


class CycleDaySensor(CycleTrackerSensor):
    """Sensor for current cycle day."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "Cycle Day", "cycle_day")
        self._attr_icon = "mdi:calendar-clock"
        self._attr_native_unit_of_measurement = "day"

    @property
    def native_value(self) -> int | None:
        """Return the current cycle day."""
        if not self.coordinator.get_last_period_start():
            return None
        today = date.today().isoformat()
        return self.coordinator.calculate_cycle_day(today)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            ATTR_CYCLE_DAY: self.native_value,
        }


class CyclePhaseSensor(CycleTrackerSensor):
    """Sensor for current cycle phase."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "Cycle Phase", "cycle_phase")
        self._attr_icon = "mdi:heart-pulse"

    @property
    def native_value(self) -> str | None:
        """Return the current cycle phase."""
        if not self.coordinator.get_last_period_start():
            return None
        today = date.today().isoformat()
        return self.coordinator.calculate_phase(today)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            ATTR_CYCLE_PHASE: self.native_value,
        }


class NextPeriodDateSensor(CycleTrackerSensor):
    """Sensor for next predicted period date."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "Next Period Date", "next_period_date")
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-star"

    @property
    def native_value(self) -> str | None:
        """Return the next predicted period date."""
        if not self.coordinator.get_last_period_start():
            return None
        today = date.today().isoformat()
        return self.coordinator.predict_next_period(today)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            ATTR_NEXT_PERIOD_DATE: self.native_value,
        }


class NextOvulationDateSensor(CycleTrackerSensor):
    """Sensor for next predicted ovulation date."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(
            coordinator, entry, "Next Ovulation Date", "next_ovulation_date"
        )
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:egg"

    @property
    def native_value(self) -> str | None:
        """Return the next predicted ovulation date."""
        if not self.coordinator.get_last_period_start():
            return None
        from datetime import date, timedelta

        last_start = self.coordinator.get_last_period_start()
        if not last_start:
            return None
        last = date.fromisoformat(last_start)
        cycle_length = self.coordinator.get_cycle_length()
        ovulation_day = cycle_length // 2
        next_ovulation = last + timedelta(days=ovulation_day)
        if next_ovulation < date.today():
            next_ovulation += timedelta(days=cycle_length)
        return next_ovulation.isoformat()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            ATTR_NEXT_OVULATION_DATE: self.native_value,
        }


class DaysUntilPeriodSensor(CycleTrackerSensor):
    """Sensor for days until next period."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "Days Until Period", "days_until_period")
        self._attr_icon = "mdi:calendar-minus"
        self._attr_native_unit_of_measurement = "days"

    @property
    def native_value(self) -> int | None:
        """Return days until next period."""
        if not self.coordinator.get_last_period_start():
            return None
        from datetime import date

        next_period = self.coordinator.predict_next_period(date.today().isoformat())
        if not next_period:
            return None
        next_date = date.fromisoformat(next_period)
        delta = (next_date - date.today()).days
        return max(0, delta)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            ATTR_DAYS_UNTIL_PERIOD: self.native_value,
        }


class DaysUntilOvulationSensor(CycleTrackerSensor):
    """Sensor for days until next ovulation."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(
            coordinator, entry, "Days Until Ovulation", "days_until_ovulation"
        )
        self._attr_icon = "mdi:calendar-plus"
        self._attr_native_unit_of_measurement = "days"

    @property
    def native_value(self) -> int | None:
        """Return days until next ovulation."""
        if not self.coordinator.get_last_period_start():
            return None
        from datetime import date

        next_ovulation = self.coordinator.get_next_ovulation_date()
        if not next_ovulation:
            return None
        next_date = date.fromisoformat(next_ovulation)
        delta = (next_date - date.today()).days
        return max(0, delta)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            ATTR_DAYS_UNTIL_OVULATION: self.native_value,
        }


class CycleStatisticsSensor(CycleTrackerSensor):
    """Sensor for cycle statistics."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "Statistics", "statistics")
        self._attr_icon = "mdi:chart-line"

    @property
    def native_value(self) -> int:
        """Return total cycles tracked."""
        stats = self.coordinator.get_statistics()
        return stats.get("total_cycles_tracked", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        stats = self.coordinator.get_statistics()
        return {
            ATTR_AVERAGE_CYCLE_LENGTH: stats.get("average_cycle_length"),
            ATTR_AVERAGE_PERIOD_LENGTH: stats.get("average_period_length"),
            ATTR_STD_DEV_CYCLE: stats.get("cycle_length_std_dev"),
            ATTR_STD_DEV_PERIOD: stats.get("period_length_std_dev"),
            ATTR_TOTAL_CYCLES_TRACKED: stats.get("total_cycles_tracked"),
            ATTR_PREDICTION_CONFIDENCE: 0.5,
        }
