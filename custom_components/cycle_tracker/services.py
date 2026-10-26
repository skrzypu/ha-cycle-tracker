"""Services for Cycle Tracker."""

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN,
    SERVICE_LOG_START,
    SERVICE_LOG_END,
)
from .coordinator import CycleTrackerCoordinator


SERVICE_LOG_START_SCHEMA = vol.Schema(
    {
        vol.Required("date"): cv.date,
        vol.Optional("flow_intensity", default="medium"): vol.In(
            ["spotting", "light", "medium", "heavy"]
        ),
    }
)

SERVICE_LOG_END_SCHEMA = vol.Schema(
    {
        vol.Required("date"): cv.date,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Cycle Tracker."""

    async def handle_log_start(call: ServiceCall) -> ServiceResponse:
        """Handle log_start service call."""
        coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][
            call.config_entry.entry_id
        ]
        date_str = call.data["date"].isoformat()
        flow_intensity = call.data["flow_intensity"]

        periods = coordinator.get_periods()
        if periods and periods[-1]["start_date"] == date_str:
            # Update existing period
            periods[-1]["end_date"] = date_str
            periods[-1]["flow_intensity"] = flow_intensity
        else:
            # Add new period
            coordinator.add_period(
                {
                    "start_date": date_str,
                    "end_date": date_str,
                    "flow_intensity": flow_intensity,
                }
            )

        await coordinator.async_save_data()
        coordinator.async_set_updated_data(coordinator._data)

        return {"success": True, "message": f"Period start logged for {date_str}"}

    async def handle_log_end(call: ServiceCall) -> ServiceResponse:
        """Handle log_end service call."""
        coordinator: CycleTrackerCoordinator = hass.data[DOMAIN][
            call.config_entry.entry_id
        ]
        date_str = call.data["date"].isoformat()

        periods = coordinator.get_periods()
        if not periods:
            return {"success": False, "message": "No period started to end"}

        # Find the period that matches or is the latest
        last_period = periods[-1]
        if last_period["end_date"] != last_period["start_date"]:
            return {"success": False, "message": "Period already ended"}

        last_period["end_date"] = date_str
        await coordinator.async_save_data()
        coordinator.async_set_updated_data(coordinator._data)

        return {"success": True, "message": f"Period end logged for {date_str}"}

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
