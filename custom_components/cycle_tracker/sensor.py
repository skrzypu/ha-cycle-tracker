"""Sensor entities for Cycle Tracker."""

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AVERAGE_CYCLE_LENGTH,
    ATTR_AVERAGE_PERIOD_LENGTH,
    ATTR_CONFIDENCE_BAND,
    ATTR_CYCLE_DAY,
    ATTR_CYCLE_PHASE,
    ATTR_DAYS_LATE,
    ATTR_DAYS_UNTIL_OVULATION,
    ATTR_DAYS_UNTIL_PERIOD,
    ATTR_ESTIMATED_FERTILE_WINDOW,
    ATTR_FERTILE_WINDOW_END,
    ATTR_FERTILE_WINDOW_START,
    ATTR_IS_LATE,
    ATTR_LIFETIME_AVERAGE_CYCLE_LENGTH,
    ATTR_LONGEST_CYCLE,
    ATTR_MARGIN_BAND,
    ATTR_MARGIN_DAYS,
    ATTR_NEXT_MARGIN_BAND,
    ATTR_NEXT_OVULATION_DATE,
    ATTR_NEXT_PERIOD_DATE,
    ATTR_OVULATION_WINDOW_END,
    ATTR_OVULATION_WINDOW_START,
    ATTR_PREDICTED_CYCLE_LENGTH,
    ATTR_PREDICTION_CONFIDENCE,
    ATTR_PREVIOUS_BAND_DAYS_AGO,
    ATTR_PREVIOUS_MARGIN_BAND,
    ATTR_SHORTEST_CYCLE,
    ATTR_STD_DEV_CYCLE,
    ATTR_STD_DEV_PERIOD,
    ATTR_TOTAL_CYCLES_TRACKED,
    ATTR_UNCERTAINTY_END,
    ATTR_UNCERTAINTY_START,
    ATTR_USABLE_CYCLE_COUNT,
    ATTR_WARNINGS,
    DOMAIN,
)
from .coordinator import CycleTrackerCoordinator
from .domain.models import Prediction
from .domain.prediction import Snapshot


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cycle Tracker sensors."""
    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[CycleTrackerSensor] = [
        CycleDaySensor(coordinator, entry),
        CycleStartDateSensor(coordinator, entry),
        CyclePhaseSensor(coordinator, entry),
        NextPeriodDateSensor(coordinator, entry),
        NextOvulationDateSensor(coordinator, entry),
        DaysUntilPeriodSensor(coordinator, entry),
        DaysUntilOvulationSensor(coordinator, entry),
        CycleStatisticsSensor(coordinator, entry),
    ]
    # Disabled by default: no entity at all rather than an unavailable one.
    if coordinator.get_enable_fertility_estimate():
        entities.append(FertilityEstimateSensor(coordinator, entry))
    async_add_entities(entities)


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

    @property
    def available(self) -> bool:
        """Mirror the coordinator's availability state."""
        return self.coordinator.available

    @property
    def _snapshot(self) -> Snapshot:
        """Return the coordinator's prediction snapshot."""
        return self.coordinator.snapshot

    @property
    def _prediction(self) -> Prediction | None:
        """Return the prediction, or None when history is insufficient."""
        return self.coordinator.snapshot.prediction


class CycleDaySensor(CycleTrackerSensor):
    """Sensor for the elapsed day of the current cycle."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "Cycle Day", "cycle_day")
        self._attr_icon = "mdi:calendar-clock"
        self._attr_native_unit_of_measurement = "day"

    @property
    def native_value(self) -> int | None:
        """Return the elapsed cycle day, unbounded by the configured length."""
        return self._snapshot.cycle_day

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            ATTR_CYCLE_DAY: self.native_value,
        }


class CycleStartDateSensor(CycleTrackerSensor):
    """Sensor for the start date of the current cycle."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "Cycle Start Date", "cycle_start_date")
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-start"

    @property
    def native_value(self) -> date | None:
        """Return the most recent recorded period start on or before today."""
        return self._snapshot.cycle_start


class CyclePhaseSensor(CycleTrackerSensor):
    """Sensor for current cycle phase."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "Cycle Phase", "cycle_phase")
        self._attr_icon = "mdi:heart-pulse"

    @property
    def native_value(self) -> str | None:
        """Return the phase derived from the ovulation center."""
        phase = self._snapshot.phase
        return phase.value if phase is not None else None

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
    def native_value(self) -> date | None:
        """Return the predicted next period date."""
        prediction = self._prediction
        if prediction is None:
            return None
        return prediction.next_period

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the uncertainty window and prediction reliability."""
        prediction = self._prediction
        attributes: dict[str, Any] = {
            ATTR_NEXT_PERIOD_DATE: (
                prediction.next_period.isoformat() if prediction is not None else None
            )
        }
        if prediction is not None:
            uncertainty_start, uncertainty_end = prediction.uncertainty
            attributes[ATTR_UNCERTAINTY_START] = uncertainty_start.isoformat()
            attributes[ATTR_UNCERTAINTY_END] = uncertainty_end.isoformat()
            attributes[ATTR_PREDICTED_CYCLE_LENGTH] = prediction.cycle_length_days
            attributes[ATTR_USABLE_CYCLE_COUNT] = prediction.usable_cycle_count
        return attributes


class NextOvulationDateSensor(CycleTrackerSensor):
    """Sensor for the next predicted ovulation center."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(
            coordinator, entry, "Next Ovulation Date", "next_ovulation_date"
        )
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:egg"

    @property
    def native_value(self) -> date | None:
        """Return the centre of the first ovulation that has not passed."""
        prediction = self._prediction
        if prediction is None:
            return None
        return prediction.next_ovulation.ovulation_center

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the windows of that upcoming ovulation."""
        prediction = self._prediction
        attributes: dict[str, Any] = {
            ATTR_NEXT_OVULATION_DATE: (
                prediction.next_ovulation.ovulation_center.isoformat()
                if prediction is not None
                else None
            )
        }
        if prediction is not None:
            ovulation_start, ovulation_end = prediction.next_ovulation.ovulation
            fertile_start, fertile_end = prediction.next_ovulation.fertile
            attributes[ATTR_OVULATION_WINDOW_START] = ovulation_start.isoformat()
            attributes[ATTR_OVULATION_WINDOW_END] = ovulation_end.isoformat()
            attributes[ATTR_FERTILE_WINDOW_START] = fertile_start.isoformat()
            attributes[ATTR_FERTILE_WINDOW_END] = fertile_end.isoformat()
        return attributes


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
        """Return days until the predicted period, zero when due or late."""
        prediction = self._prediction
        if prediction is None:
            return None
        return prediction.days_until_period

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the late state that distinguishes overdue from due today."""
        attributes: dict[str, Any] = {ATTR_DAYS_UNTIL_PERIOD: self.native_value}
        prediction = self._prediction
        if prediction is not None:
            attributes[ATTR_IS_LATE] = prediction.is_late
            attributes[ATTR_DAYS_LATE] = prediction.days_late
        return attributes


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
        """Return days until the predicted ovulation center."""
        prediction = self._prediction
        if prediction is None:
            return None
        return prediction.days_until_ovulation

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
        """Return the number of recorded periods."""
        return self._snapshot.statistics.total_cycles_tracked

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the windowed statistics, confidence and warnings."""
        snapshot = self._snapshot
        statistics = snapshot.statistics
        band = statistics.confidence_band
        attributes: dict[str, Any] = {
            ATTR_AVERAGE_CYCLE_LENGTH: statistics.average_cycle_length,
            ATTR_LIFETIME_AVERAGE_CYCLE_LENGTH: (
                statistics.lifetime_average_cycle_length
            ),
            ATTR_AVERAGE_PERIOD_LENGTH: statistics.average_period_length,
            ATTR_STD_DEV_CYCLE: statistics.cycle_length_std_dev,
            ATTR_STD_DEV_PERIOD: statistics.period_length_std_dev,
            ATTR_SHORTEST_CYCLE: statistics.shortest_cycle,
            ATTR_LONGEST_CYCLE: statistics.longest_cycle,
            ATTR_TOTAL_CYCLES_TRACKED: statistics.total_cycles_tracked,
            ATTR_PREDICTION_CONFIDENCE: statistics.confidence,
            ATTR_CONFIDENCE_BAND: band.value if band is not None else None,
        }
        prediction = snapshot.prediction
        if prediction is not None:
            attributes[ATTR_USABLE_CYCLE_COUNT] = prediction.usable_cycle_count
            attributes[ATTR_WARNINGS] = [
                {"kind": str(warning.kind), "period_id": str(warning.period_id)}
                for warning in prediction.warnings
            ]
        return attributes


def _iso_window(window: tuple[date, date] | None) -> tuple[str, str] | None:
    """Serialize a date window for an entity attribute."""
    if window is None:
        return None
    return window[0].isoformat(), window[1].isoformat()


class FertilityEstimateSensor(CycleTrackerSensor):
    """Sensor for the estimate of the current fertile window and its margin."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "Fertility Estimate", "fertility_estimate")
        self._attr_icon = "mdi:flower"
        self._attr_translation_key = "fertility_estimate"

    @property
    def native_value(self) -> str:
        """Return the stable technical state token."""
        return self._snapshot.fertility.state.value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the base window, the margin band and their provenance."""
        estimate = self._snapshot.fertility
        band = estimate.confidence_band
        return {
            ATTR_ESTIMATED_FERTILE_WINDOW: _iso_window(estimate.fertile_window),
            ATTR_MARGIN_BAND: _iso_window(estimate.margin_band),
            ATTR_PREVIOUS_MARGIN_BAND: _iso_window(estimate.previous_margin_band),
            ATTR_PREVIOUS_BAND_DAYS_AGO: estimate.previous_band_days_ago,
            ATTR_NEXT_MARGIN_BAND: _iso_window(estimate.next_margin_band),
            ATTR_MARGIN_DAYS: estimate.margin_days,
            ATTR_PREDICTION_CONFIDENCE: estimate.confidence,
            ATTR_CONFIDENCE_BAND: band.value if band is not None else None,
            ATTR_USABLE_CYCLE_COUNT: estimate.usable_cycle_count,
        }
