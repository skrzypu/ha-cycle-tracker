"""Constants for the Cycle Tracker integration."""

from homeassistant.const import Platform

DOMAIN = "cycle_tracker"

# Platforms
PLATFORMS = [Platform.SENSOR, Platform.CALENDAR]

# Configuration keys
CONF_CYCLE_LENGTH = "cycle_length"
CONF_PERIOD_LENGTH = "period_length"
CONF_LAST_PERIOD_START = "last_period_start"
CONF_PREDICTION_ALGORITHM = "prediction_algorithm"
CONF_NOTIFICATION_OFFSET_DAYS = "notification_offset_days"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"
CONF_NOTIFICATION_TIME = "notification_time"

# Default values
DEFAULT_CYCLE_LENGTH = 28
DEFAULT_PERIOD_LENGTH = 5
DEFAULT_PREDICTION_ALGORITHM = "weighted_moving_average"
DEFAULT_NOTIFICATION_OFFSET_DAYS = 2
DEFAULT_ENABLE_NOTIFICATIONS = False
DEFAULT_NOTIFICATION_TIME = "08:00"

# Prediction algorithms
PREDICTION_ALGORITHMS = [
    "arithmetic_mean",
    "weighted_moving_average",
]

# Attributes
ATTR_CYCLE_DAY = "cycle_day"
ATTR_CYCLE_PHASE = "cycle_phase"
ATTR_NEXT_PERIOD_DATE = "next_period_date"
ATTR_NEXT_OVULATION_DATE = "next_ovulation_date"
ATTR_CYCLE_LENGTH = "cycle_length"
ATTR_PERIOD_LENGTH = "period_length"
ATTR_DAYS_UNTIL_PERIOD = "days_until_period"
ATTR_DAYS_UNTIL_OVULATION = "days_until_ovulation"
ATTR_PREDICTION_CONFIDENCE = "prediction_confidence"
ATTR_AVERAGE_CYCLE_LENGTH = "average_cycle_length"
ATTR_AVERAGE_PERIOD_LENGTH = "average_period_length"
ATTR_STD_DEV_CYCLE = "std_dev_cycle"
ATTR_STD_DEV_PERIOD = "std_dev_period"
ATTR_TOTAL_CYCLES_TRACKED = "total_cycles_tracked"

# Cycle phases
CYCLE_PHASE_MENSTRUAL = "menstrual"
CYCLE_PHASE_FOLLICULAR = "follicular"
CYCLE_PHASE_OVULATORY = "ovulatory"
CYCLE_PHASE_LUTEAL = "luteal"

CYCLE_PHASES = [
    CYCLE_PHASE_MENSTRUAL,
    CYCLE_PHASE_FOLLICULAR,
    CYCLE_PHASE_OVULATORY,
    CYCLE_PHASE_LUTEAL,
]

# Services
SERVICE_LOG_START = "log_start"
SERVICE_LOG_END = "log_end"

# Events
EVENT_PERIOD_START = f"{DOMAIN}_period_start"
EVENT_PERIOD_END = f"{DOMAIN}_period_end"
EVENT_OVULATION = f"{DOMAIN}_ovulation"
EVENT_NEXT_PERIOD = f"{DOMAIN}_next_period"

# Update interval (hours)
DEFAULT_UPDATE_INTERVAL_HOURS = 6

# Storage
STORAGE_KEY = f"{DOMAIN}_data"
STORAGE_VERSION = 1
