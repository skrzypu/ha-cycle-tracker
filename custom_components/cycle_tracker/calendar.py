"""Calendar entity for Cycle Tracker."""

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import CycleTrackerCoordinator
from .domain.events import EventKind

_SUMMARIES = {
    EventKind.PERIOD: "Predicted Period",
    EventKind.OVULATION: "Ovulation",
    EventKind.FERTILE: "Fertile Window",
}

_DESCRIPTIONS = {
    EventKind.PERIOD: "Estimated from your recorded cycle history",
    EventKind.OVULATION: "Estimated ovulation window — not a contraceptive guarantee",
    EventKind.FERTILE: "Estimated fertile window — not a contraceptive guarantee",
}


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
        today = dt_util.now().date()
        for evt in events:
            if evt.end >= today:
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
        """Get recorded and projected cycle events."""
        events = self._get_recorded_events()
        events.extend(self._get_projected_events())
        events.sort(key=lambda event: event.start)
        return events

    def _get_recorded_events(self) -> list[CalendarEvent]:
        """Map recorded periods, keeping the stored row shape unchanged."""
        events: list[CalendarEvent] = []
        for period in self.coordinator.get_periods():
            try:
                start = date.fromisoformat(period["start_date"])
                raw_end = period.get("end_date") or period["start_date"]
                end = date.fromisoformat(raw_end) + timedelta(days=1)
            except (KeyError, TypeError, ValueError):
                continue
            events.append(
                CalendarEvent(
                    summary="Period",
                    start=start,
                    end=end,
                    description=f"Flow: {period.get('flow_intensity', 'medium')}",
                )
            )
        return events

    def _get_projected_events(self) -> list[CalendarEvent]:
        """Map the domain projection of the prediction to calendar events."""
        events: list[CalendarEvent] = []
        for event in self.coordinator.snapshot.events:
            summary = _SUMMARIES.get(event.kind)
            if summary is None:
                continue
            events.append(
                CalendarEvent(
                    summary=summary,
                    start=event.start,
                    end=event.end + timedelta(days=1),
                    description=_DESCRIPTIONS[event.kind],
                )
            )
        return events

    def _get_events_in_range(
        self, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get events within a specific range."""
        start = start_date.date() if isinstance(start_date, datetime) else start_date
        end = end_date.date() if isinstance(end_date, datetime) else end_date
        all_events = self._get_events()
        return [evt for evt in all_events if evt.start < end and evt.end > start]
