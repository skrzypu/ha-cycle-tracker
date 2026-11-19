"""Constants for the Cycle Tracker integration."""

from homeassistant.const import Platform

DOMAIN = "cycle_tracker"

# Platforms
PLATFORMS = [Platform.SENSOR, Platform.CALENDAR, Platform.BINARY_SENSOR]

# Configuration keys
CONF_CYCLE_LENGTH = "cycle_length"
CONF_PERIOD_LENGTH = "period_length"
CONF_LAST_PERIOD_START = "last_period_start"
CONF_PREDICTION_ALGORITHM = "prediction_algorithm"
CONF_NOTIFICATION_OFFSET_DAYS = "notification_offset_days"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"
CONF_NOTIFICATION_TIME = "notification_time"

# Google Sheets source-of-truth configuration keys
CONF_SPREADSHEET_ID = "spreadsheet_id"
CONF_WORKSHEET = "worksheet"
CONF_SERVICE_ACCOUNT_FILE = "service_account_file"
CONF_POLL_INTERVAL = "poll_interval"
CONF_IMPORT_CACHED = "import_cached_periods"

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
    "median",
]

# Data warning kinds
WARNING_OUTLIER = "outlier"
WARNING_GAP = "gap"
WARNING_MISSING_FLOW = "missing_flow"

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
ATTR_CONFIDENCE_BAND = "confidence_band"
ATTR_AVERAGE_CYCLE_LENGTH = "average_cycle_length"
ATTR_AVERAGE_PERIOD_LENGTH = "average_period_length"
ATTR_STD_DEV_CYCLE = "cycle_length_std_dev"
ATTR_STD_DEV_PERIOD = "period_length_std_dev"
ATTR_SHORTEST_CYCLE = "shortest_cycle"
ATTR_LONGEST_CYCLE = "longest_cycle"
ATTR_TOTAL_CYCLES_TRACKED = "total_cycles_tracked"
ATTR_USABLE_CYCLE_COUNT = "usable_cycle_count"
ATTR_PREDICTED_CYCLE_LENGTH = "predicted_cycle_length"
ATTR_UNCERTAINTY_START = "uncertainty_start"
ATTR_UNCERTAINTY_END = "uncertainty_end"
ATTR_OVULATION_WINDOW_START = "ovulation_window_start"
ATTR_OVULATION_WINDOW_END = "ovulation_window_end"
ATTR_FERTILE_WINDOW_START = "fertile_window_start"
ATTR_FERTILE_WINDOW_END = "fertile_window_end"
ATTR_IS_LATE = "is_late"
ATTR_DAYS_LATE = "days_late"
ATTR_WARNINGS = "warnings"

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

# Update interval (hours) — kept for compatibility; new code uses poll interval
DEFAULT_UPDATE_INTERVAL_HOURS = 6

# Google Sheets poll interval (minutes)
DEFAULT_POLL_INTERVAL_MINUTES = 5
MIN_POLL_INTERVAL_MINUTES = 1
MAX_POLL_INTERVAL_MINUTES = 60

# Storage
STORAGE_KEY = f"{DOMAIN}_data"
STORAGE_VERSION = 1

# Read-through cache for remote repositories
STORAGE_KEY_SYNC_CACHE = f"{DOMAIN}_sync_cache"
STORAGE_VERSION_SYNC_CACHE = 1
