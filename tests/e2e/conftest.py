"""Fixtures that drive the integration the way a user or automation does.

End-to-end tests must not reach into the coordinator: history enters only
through the ``log_start``/``log_end`` services and the result leaves only
through entity states and the calendar component's ``get_events`` service. The
fixtures here keep that boundary in one place so a test cannot accidentally
shortcut it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import pytest
from homeassistant.components.calendar import (
    EVENT_END_DATETIME,
    EVENT_START_DATETIME,
    SERVICE_GET_EVENTS,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cycle_tracker.const import (
    CONF_CYCLE_LENGTH,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_NOTIFICATION_OFFSET_DAYS,
    CONF_NOTIFICATION_TIME,
    CONF_PERIOD_LENGTH,
    CONF_PREDICTION_ALGORITHM,
    DOMAIN,
    SERVICE_LOG_END,
    SERVICE_LOG_START,
)

CALENDAR_DOMAIN = "calendar"
CALENDAR_ENTITY = "calendar.menstrual_cycle"


@pytest.fixture
async def started_entry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    frozen_today: date,
) -> AsyncIterator[MockConfigEntry]:
    """Set the integration up and tear it down like Home Assistant would."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    yield config_entry

    if config_entry.entry_id in hass.data.get(DOMAIN, {}):
        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()


@pytest.fixture
def state_of(hass: HomeAssistant) -> Callable[[str], State]:
    """Return an accessor that fails when an expected entity is missing."""

    def _state_of(entity_id: str) -> State:
        state = hass.states.get(entity_id)
        assert state is not None, f"{entity_id} was not created"
        return state

    return _state_of


@pytest.fixture
def log_period(
    hass: HomeAssistant, started_entry: MockConfigEntry
) -> Callable[..., Awaitable[None]]:
    """Return a helper that records a period through the public services."""

    async def _log_period(
        start: date,
        end: date | None = None,
        flow: str = "medium",
    ) -> None:
        response = await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_START,
            {"date": start, "flow_intensity": flow},
            blocking=True,
            return_response=True,
        )
        assert response is not None
        assert response["success"] is True, response

        if end is not None:
            response = await hass.services.async_call(
                DOMAIN,
                SERVICE_LOG_END,
                {"date": end},
                blocking=True,
                return_response=True,
            )
            assert response is not None
            assert response["success"] is True, response

        await hass.async_block_till_done()

    return _log_period


@pytest.fixture
def set_algorithm(
    hass: HomeAssistant, started_entry: MockConfigEntry
) -> Callable[[str], Awaitable[None]]:
    """Return a helper that changes the prediction algorithm via the options flow."""

    async def _set_algorithm(algorithm: str) -> None:
        result = await hass.config_entries.options.async_init(started_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_CYCLE_LENGTH: 28,
                CONF_PERIOD_LENGTH: 5,
                CONF_PREDICTION_ALGORITHM: algorithm,
                CONF_NOTIFICATION_OFFSET_DAYS: 2,
                CONF_ENABLE_NOTIFICATIONS: False,
                CONF_NOTIFICATION_TIME: "08:00",
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        # The entry update listener reloads the integration before this returns.
        await hass.async_block_till_done()

    return _set_algorithm


@pytest.fixture
def calendar_events(
    hass: HomeAssistant,
) -> Callable[[date, date], Awaitable[list[dict[str, Any]]]]:
    """Return a helper that reads the calendar through its public service.

    The payload is the component's ``get_events`` response for the one calendar
    entity: ``start``/``end`` are ISO dates with an exclusive ``end``, exactly
    as the calendar API exposes them.
    """

    async def _calendar_events(start: date, end: date) -> list[dict[str, Any]]:
        response = await hass.services.async_call(
            CALENDAR_DOMAIN,
            SERVICE_GET_EVENTS,
            {
                EVENT_START_DATETIME: datetime.combine(start, time.min, tzinfo=UTC),
                EVENT_END_DATETIME: datetime.combine(end, time.min, tzinfo=UTC),
            },
            target={"entity_id": CALENDAR_ENTITY},
            blocking=True,
            return_response=True,
        )
        assert response is not None
        return response[CALENDAR_ENTITY]["events"]

    return _calendar_events


@pytest.fixture
def closed_period(
    log_period: Callable[..., Awaitable[None]],
) -> Callable[..., Awaitable[None]]:
    """Return a helper that records a completed five-day period.

    ``log_end`` only closes the newest open row, so history has to be recorded
    oldest first; the last period of a scenario is left open on purpose.
    """

    async def _closed_period(start: date, length: int = 5) -> None:
        await log_period(start, start + timedelta(days=length - 1))

    return _closed_period
