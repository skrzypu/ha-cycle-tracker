"""Tests for the calendar adapter projecting domain events."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEvent
from homeassistant.const import Platform

from custom_components.cycle_tracker.calendar import MenstrualCycleCalendar
from custom_components.cycle_tracker.coordinator import CycleTrackerCoordinator


def _calendar_entity(hass) -> MenstrualCycleCalendar:
    """Return the set-up calendar entity."""
    component = hass.data["entity_components"][Platform.CALENDAR]
    entity = component.get_entity("calendar.menstrual_cycle")
    assert isinstance(entity, MenstrualCycleCalendar)
    return entity


def _summaries(events: list[CalendarEvent]) -> list[str]:
    """Return the event summaries in order."""
    return [event.summary for event in events]


async def test_calendar_maps_recorded_and_projected_events(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, str]],
    frozen_today: date,
) -> None:
    """A range returns recorded periods plus the projected prediction events."""
    for weeks_ago in (8, 4, 0):
        coordinator.add_period(
            period_row(frozen_today - timedelta(days=3) - timedelta(weeks=weeks_ago))
        )
    coordinator.async_update_listeners()

    events = await _calendar_entity(hass).async_get_events(
        hass,
        datetime(2026, 9, 1),
        datetime(2026, 12, 31),
    )

    summaries = _summaries(events)
    assert summaries.count("Period") == 3
    assert summaries.count("Predicted Period") == 1
    assert summaries.count("Ovulation") == 1
    assert summaries.count("Fertile Window") == 1

    recorded = [event for event in events if event.summary == "Period"]
    assert recorded[0].start == date(2026, 9, 15)
    assert recorded[0].end == date(2026, 9, 20)

    predicted = [event for event in events if event.summary == "Predicted Period"]
    assert predicted[0].start == date(2026, 12, 8)
    assert predicted[0].end == date(2026, 12, 13)

    ovulation = [event for event in events if event.summary == "Ovulation"]
    assert ovulation[0].start == date(2026, 12, 20)
    assert ovulation[0].end == date(2026, 12, 25)

    fertile = [event for event in events if event.summary == "Fertile Window"]
    assert fertile[0].start == date(2026, 12, 17)
    assert fertile[0].end == date(2026, 12, 23)


async def test_calendar_without_a_prediction_only_has_recorded_periods(
    hass,
    coordinator: CycleTrackerCoordinator,
    period_row: Callable[..., dict[str, str]],
    frozen_today: date,
) -> None:
    """Recorded history stays visible when no prediction exists."""
    coordinator.add_period(period_row(frozen_today))
    coordinator.async_update_listeners()

    events = await _calendar_entity(hass).async_get_events(
        hass,
        datetime(2026, 11, 1),
        datetime(2026, 12, 1),
    )

    assert _summaries(events) == ["Period"]
