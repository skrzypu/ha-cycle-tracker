"""Calendar entity for Cycle Tracker."""

from datetime import date, datetime, timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
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
    """Set up Cycle Tracker calendar."""
    coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MenstrualCycleCalendar(coordinator, entry)])


class MenstrualCycleCalendar(
    CoordinatorEntity[CycleTrackerCoordinator], CalendarEntity
):
    """Calendar entity for menstrual cycle."""

    def __init__(
        self, coordinator: CycleTrackerCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Menstrual Cycle"
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Cycle Tracker",
            "manufacturer": "Cycle Tracker",
            "model": "Menstrual Cycle Tracker",
        }

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        events = self._get_events()
        if not events:
            return None
        now = datetime.now()
        for evt in events:
            if evt.end >= now:
                return evt
        return events[-1] if events else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Get events within a date range."""
        return self._get_events_in_range(start_date, end_date)

    def _get_events(self) -> list[CalendarEvent]:
        """Get all cycle events."""
        events = []
        periods = self.coordinator.get_periods()
        if not periods:
            return events

        for period in periods:
            start = datetime.fromisoformat(period["start_date"])
            end = datetime.fromisoformat(period["end_date"]) + timedelta(days=1)
            events.append(
                CalendarEvent(
                    summary="Period",
                    start=start,
                    end=end,
                    description=f"Flow: {period.get('flow_intensity', 'medium')}",
                )
            )

        # Add predicted periods
        last_start = self.coordinator.get_last_period_start()
        if last_start:
            cycle_length = self.coordinator.get_cycle_length()
            last = date.fromisoformat(last_start)
            for i in range(1, 13):  # Next 12 cycles
                pred_start = last + timedelta(days=cycle_length * i)
                pred_end = pred_start + timedelta(
                    days=self.coordinator.get_period_length()
                )
                events.append(
                    CalendarEvent(
                        summary="Predicted Period",
                        start=datetime.combine(pred_start, datetime.min.time()),
                        end=datetime.combine(pred_end, datetime.min.time()),
                        description="Predicted based on average cycle length",
                    )
                )

        return events

    def _get_events_in_range(
        self, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get events within a specific range."""
        all_events = self._get_events()
        return [
            evt for evt in all_events if evt.start < end_date and evt.end > start_date
        ]
