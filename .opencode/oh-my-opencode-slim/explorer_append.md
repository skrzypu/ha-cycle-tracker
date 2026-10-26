## Project-Specific Explorer Rules for ha-cycle-tracker

### Key Search Patterns

#### Python (custom_components/cycle_tracker)
```bash
# Sensor entities
ast_grep_search pattern='class $NAME.*SensorEntity' lang=python

# Config flow steps
ast_grep_search pattern='async_step_$STEP' lang=python paths=["custom_components/cycle_tracker/config_flow.py"]

# Service handlers
ast_grep_search pattern='async_$SERVICE' lang=python paths=["custom_components/cycle_tracker/services.py"]

# Coordinator update
ast_grep_search pattern='_async_update_data' lang=python

# HA storage usage
ast_grep_search pattern='Store\(' lang=python

# Prediction algorithms
ast_grep_search pattern='class $NAME.*Strategy' lang=python paths=["custom_components/cycle_tracker/coordinator.py"]

# Calendar entity
ast_grep_search pattern='class $NAME.*CalendarEntity' lang=python
```

#### Test & Fixture Navigation
```bash
# Persistence schema references
grep -r "STORAGE_KEY\|STORAGE_VERSION" --include="*.py" custom_components/

# Prediction algorithm entry points
grep -r "class .*Strategy" --include="*.py"

# Shared fixture files
ls tests/fixtures/*.json
```

### Common Navigation Tasks

#### "Trace prediction from UI to algorithm"
1. `custom_components/cycle_tracker/sensor.py` → `NextPeriodDateSensor.native_value`
2. → `coordinator.py` → `predict_next_period()`
3. → `coordinator.py` → `calculate_cycle_day()`, `calculate_phase()`

#### "Find all period logging entry points"
1. `services.yaml` → `cycle_tracker.log_start`, `cycle_tracker.log_end`
2. `services.py` → `handle_log_start`, `handle_log_end`
3. → `coordinator.py` → `add_period()` → `async_save_data()`

#### "Locate test fixtures for irregular cycles"
- `tests/fixtures/irregular_cycles.json` (Python)

#### "Find all HA selector usage in config flow"
- `config_flow.py` → `async_step_*` methods → `Selector` objects

### Symbol Index (Mental Map)

#### Python HA Domain
- `CycleTrackerCoordinator` - `DataUpdateCoordinator`, holds period data, calculations
- `CycleDaySensor`, `CyclePhaseSensor`, `NextPeriodDateSensor` - `SensorEntity`
- `MenstrualCycleCalendar` - `CalendarEntity`
- `CycleTrackerConfigFlow` - `ConfigFlow` with 3 steps
- `ArithmeticMeanStrategy`, `WeightedMovingAverageStrategy` - prediction algorithms
- `StandardDeviationCalculator` - statistics

#### Python HA Services
- `handle_log_start` - logs period start with flow intensity
- `handle_log_end` - logs period end
- Both update storage and trigger coordinator refresh

### File Ownership (for Parallel Dispatch)
| Area | Owner Agent | Files |
|------|-------------|-------|
| Python Coordinator/Algorithms | @python-ha-component | `custom_components/cycle_tracker/coordinator.py` |
| Python Sensors/Calendar | @python-ha-component | `custom_components/cycle_tracker/sensor.py`, `calendar.py` |
| Python Config Flow | @python-ha-component | `custom_components/cycle_tracker/config_flow.py` |
| Python Services | @python-ha-component | `custom_components/cycle_tracker/services.py` |
| Python Tests (unit/integration) | @test-engineer | `tests/unit/**`, `tests/integration/**` |
| Contract Tests | @test-engineer | `tests/contract/**`, `scripts/validate_contract.py` |
| Lovelace Card | @design-reviewer + @fixer | `custom_components/cycle_tracker/lovelace/**` |
| CI/Pre-commit | @test-engineer | `.github/workflows/ci.yml`, `.pre-commit-config.yaml` |
