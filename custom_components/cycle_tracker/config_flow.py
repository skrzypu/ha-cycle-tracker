"""Config flow for Cycle Tracker."""

from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_CYCLE_LENGTH,
    CONF_PERIOD_LENGTH,
    CONF_LAST_PERIOD_START,
    CONF_PREDICTION_ALGORITHM,
    CONF_NOTIFICATION_OFFSET_DAYS,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_NOTIFICATION_TIME,
    DEFAULT_CYCLE_LENGTH,
    DEFAULT_PERIOD_LENGTH,
    DEFAULT_PREDICTION_ALGORITHM,
    DEFAULT_NOTIFICATION_OFFSET_DAYS,
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_NOTIFICATION_TIME,
    PREDICTION_ALGORITHMS,
)


class CycleTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Cycle Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - basic configuration."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_preferences()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CYCLE_LENGTH,
                        default=DEFAULT_CYCLE_LENGTH,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=20,
                            max=45,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_PERIOD_LENGTH,
                        default=DEFAULT_PERIOD_LENGTH,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=2,
                            max=10,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_LAST_PERIOD_START,
                    ): selector.DateSelector(),
                }
            ),
            description_placeholders={
                "cycle_length_help": "Average length of your menstrual cycle in days (typically 21-35)",
                "period_length_help": "Average length of your period in days (typically 3-7)",
            },
        )

    async def async_step_preferences(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the preferences step."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_notifications()

        return self.async_show_form(
            step_id="preferences",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PREDICTION_ALGORITHM,
                        default=DEFAULT_PREDICTION_ALGORITHM,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=PREDICTION_ALGORITHMS,
                            translation_key="prediction_algorithm",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_NOTIFICATION_OFFSET_DAYS,
                        default=DEFAULT_NOTIFICATION_OFFSET_DAYS,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=14,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            description_placeholders={
                "algorithm_help": "Arithmetic Mean: simple average. Weighted Moving Average: recent cycles weighted more heavily.",
            },
        )

    async def async_step_notifications(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the notifications step."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="Cycle Tracker", data=self._data)

        return self.async_show_form(
            step_id="notifications",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENABLE_NOTIFICATIONS,
                        default=DEFAULT_ENABLE_NOTIFICATIONS,
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_NOTIFICATION_TIME,
                        default=DEFAULT_NOTIFICATION_TIME,
                    ): selector.TimeSelector(),
                }
            ),
            description_placeholders={
                "notifications_help": "Enable notifications for period start, ovulation, and upcoming period reminders.",
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return CycleTrackerOptionsFlow(config_entry)


class CycleTrackerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Cycle Tracker."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CYCLE_LENGTH,
                        default=self.config_entry.data.get(
                            CONF_CYCLE_LENGTH, DEFAULT_CYCLE_LENGTH
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=20,
                            max=45,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_PERIOD_LENGTH,
                        default=self.config_entry.data.get(
                            CONF_PERIOD_LENGTH, DEFAULT_PERIOD_LENGTH
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=2,
                            max=10,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_PREDICTION_ALGORITHM,
                        default=self.config_entry.data.get(
                            CONF_PREDICTION_ALGORITHM, DEFAULT_PREDICTION_ALGORITHM
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=PREDICTION_ALGORITHMS,
                            translation_key="prediction_algorithm",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_NOTIFICATION_OFFSET_DAYS,
                        default=self.config_entry.data.get(
                            CONF_NOTIFICATION_OFFSET_DAYS,
                            DEFAULT_NOTIFICATION_OFFSET_DAYS,
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=14,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_ENABLE_NOTIFICATIONS,
                        default=self.config_entry.data.get(
                            CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS
                        ),
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_NOTIFICATION_TIME,
                        default=self.config_entry.data.get(
                            CONF_NOTIFICATION_TIME, DEFAULT_NOTIFICATION_TIME
                        ),
                    ): selector.TimeSelector(),
                }
            ),
        )
