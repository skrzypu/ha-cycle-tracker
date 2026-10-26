## Project-Specific Fixer Rules for ha-cycle-tracker

### Python HA Component (custom_components/cycle_tracker)

#### Structure
```
custom_components/cycle_tracker/
├── __init__.py           # Setup, coordinator, services registration
├── config_flow.py        # ConfigFlow with 3 steps: basic, preferences, notifications
├── sensor.py             # 7 sensors: CycleDay, CyclePhase, NextPeriod, NextOvulation, DaysUntilPeriod, DaysUntilOvulation, Statistics
├── calendar.py           # MenstrualCycleCalendarEntity
├── services.yaml         # log_start, log_end service definitions
├── const.py              # DOMAIN, ATTR_*, SERVICE_*, CONF_*, DEFAULT_*, PREDICTION_ALGORITHMS
├── coordinator.py        # DataUpdateCoordinator with storage, cycle calculations, statistics
├── services.py           # Service handlers for log_start, log_end
└── lovelace/             # Custom card (TypeScript, separate build)
    ├── cycle-tracker-card.ts
    └── cycle-tracker-card.js (built)
```

#### Coordinator Pattern
- Extend `DataUpdateCoordinator`
- `_async_update_data()` loads from HA Store
- Cycle calculations: cycle day, phase, next period, ovulation
- Statistics: mean, std dev, cycle counts
- `async_save_data()` persists to HA Store

#### Prediction Algorithms (Pure Python)
- `ArithmeticMeanStrategy` - simple average of cycle lengths
- `WeightedMovingAverageStrategy` - recent cycles weighted more heavily
- `StandardDeviationCalculator` - population std dev for cycle/period lengths
- All in `coordinator.py` for now, can be extracted to `algorithms.py` later

#### Config Flow (3 Steps)
1. **Basic**: cycle_length, period_length, last_period_start (date selector)
2. **Preferences**: prediction_algorithm (select), notification_offset_days (number)
3. **Notifications**: enable_notifications (boolean), notification_time (time selector)
- Options flow for reconfiguration

#### Sensors (7 entities)
- `CycleDaySensor` - current day in cycle (1-based)
- `CyclePhaseSensor` - menstrual/follicular/ovulatory/luteal
- `NextPeriodDateSensor` - predicted next period start (date)
- `NextOvulationDateSensor` - predicted ovulation date (date)
- `DaysUntilPeriodSensor` - days until next period
- `DaysUntilOvulationSensor` - days until next ovulation
- `CycleStatisticsSensor` - aggregate stats (avg, std dev, count)

#### Calendar Entity
- `MenstrualCycleCalendar` - shows past periods + predicted future periods
- Implements `async_get_events()` for date range queries

#### Services
- `log_start` - log period start date + flow intensity
- `log_end` - log period end date
- Both update storage and trigger coordinator refresh

#### Testing (pytest)
- `pytest-homeassistant-custom-component` for integration tests
- Unit tests for coordinator calculations
- Fixtures/builders in `tests/` for shared test data
- Mock `CycleTrackerCoordinator` for sensor/calendar tests

#### Code Quality
- **Python**: ruff, mypy (strict), pytest passes
- **Pre-commit**: All hooks pass before commit
- **No direct commits/pushes** - require explicit user permission

#### Verification (from skills)
- **test-driven-development**: Red → Green → Refactor for every algorithm/feature
- **verification-before-completion**: Show test output, contract validation, lint results
- **simplify**: After implementation, look for complexity to reduce
