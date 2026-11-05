# Cycle Tracker

A Home Assistant custom integration for menstrual cycle tracking, with cycle-length prediction calculated locally in pure Python.

## Features

- Current cycle day and cycle phase (`menstrual`, `follicular`, `ovulatory`, `luteal`)
- Predicted next period date and next ovulation date
- Countdown sensors for days until the next period and the next ovulation
- Cycle statistics: average cycle length, average period length, standard deviations, total cycles tracked
- Calendar entity listing recorded periods plus 12 predicted future periods
- Two services to log period start and period end, including flow intensity
- Two selectable prediction algorithms: arithmetic mean and weighted moving average
- Fully local: no cloud calls, no external API, no telemetry

## Requirements

- Home Assistant **2026.1.0** or newer (declared in `custom_components/cycle_tracker/manifest.json` and `hacs.json`)
- HACS, if you want to use the HACS installation path (manual installation works without it)

## Installation

This integration is **not** part of the HACS default catalog, so it has to be added as a custom repository.

### HACS (custom repository)

1. Open HACS and use the three-dot menu → **Custom repositories**.
2. Add `https://github.com/skrzypu/ha-cycle-tracker` with category **Integration**.
3. Search for **Cycle Tracker** in HACS and download it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration**, search for **Cycle Tracker** and open the config flow.

### Manual installation

1. Copy the `custom_components/cycle_tracker/` directory from this repository into your Home Assistant configuration directory, so that you end up with `<config>/custom_components/cycle_tracker/`.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & Services → Add Integration → Cycle Tracker**.

## Configuration

The config flow has three steps:

| Step | Fields |
| --- | --- |
| Cycle settings | `cycle_length` (20–45, default 28), `period_length` (2–10, default 5), `last_period_start` (date) |
| Prediction preferences | `prediction_algorithm` (default `weighted_moving_average`), `notification_offset_days` (0–14, default 2) |
| Notifications | `enable_notifications` (default false), `notification_time` (default `08:00`) |

All settings can be changed afterwards through **Configure** on the integration entry, which exposes cycle length, period length, prediction algorithm, notification offset, and the two notification preferences in a single step.

### Prediction

Cycle lengths are derived from the differences between consecutive recorded period start dates.

- Once at least three periods have been logged (two or more cycle lengths), the next period is predicted from the most recent six cycle lengths, using the algorithm selected in the options.
- With fewer records, the configured `cycle_length` is used instead.
- `arithmetic_mean` averages all recorded cycle lengths equally.
- `weighted_moving_average` weights newer cycles more heavily than older ones.
- The next ovulation is estimated at half the configured cycle length after the last recorded period start.

Entities are recalculated every 6 hours and refreshed immediately whenever a period is logged.

## Entities

All entities are grouped under a single **Cycle Tracker** device.

| Entity ID | Friendly name | Description |
| --- | --- | --- |
| `sensor.cycle_tracker_cycle_day` | Cycle Tracker Cycle Day | Day number within the current cycle |
| `sensor.cycle_tracker_cycle_phase` | Cycle Tracker Cycle Phase | `menstrual`, `follicular`, `ovulatory` or `luteal` |
| `sensor.cycle_tracker_next_period_date` | Cycle Tracker Next Period Date | Predicted start date of the next period |
| `sensor.cycle_tracker_next_ovulation_date` | Cycle Tracker Next Ovulation Date | Predicted date of the next ovulation |
| `sensor.cycle_tracker_days_until_period` | Cycle Tracker Days Until Period | Days remaining until the predicted next period (never negative) |
| `sensor.cycle_tracker_days_until_ovulation` | Cycle Tracker Days Until Ovulation | Days remaining until the predicted next ovulation (never negative) |
| `sensor.cycle_tracker_statistics` | Cycle Tracker Statistics | Total number of tracked cycles; attributes: `average_cycle_length`, `average_period_length`, `cycle_length_std_dev`, `period_length_std_dev`, `total_cycles_tracked`, `prediction_confidence` |
| `calendar.menstrual_cycle` | Menstrual Cycle | Recorded periods and 12 predicted future periods |

Sensors return an unknown state until the first period start has been recorded. Entity IDs can be renamed from the entity settings, so they are not guaranteed to stay exactly as listed above.

## Services

Both services resolve the configuration entry from the entity or device they are called on, so the action has to be targeted at a Cycle Tracker entity or device.

| Service | Field | Required | Type / allowed values | Description |
| --- | --- | --- | --- | --- |
| `cycle_tracker.log_start` | `date` | yes | date (`YYYY-MM-DD`) | Start date of the period |
| `cycle_tracker.log_start` | `flow_intensity` | no | `spotting`, `light`, `medium`, `heavy` (default `medium`) | Intensity of the flow |
| `cycle_tracker.log_end` | `date` | yes | date (`YYYY-MM-DD`) | End date of the period |

Both services return a response object with `success` (boolean) and `message` (string). Logging a period end when no period has been started, or ending a period that was already ended, returns `success: false`.

## Example

Service call from a script:

```yaml
alias: Log period start
sequence:
  - action: cycle_tracker.log_start
    target:
      entity_id: sensor.cycle_tracker_cycle_day
    data:
      date: "2026-10-15"
      flow_intensity: medium
  - action: cycle_tracker.log_end
    target:
      entity_id: sensor.cycle_tracker_cycle_day
    data:
      date: "2026-10-20"
```

Automation that notifies the day before a predicted period:

```yaml
alias: Cycle Tracker - period reminder
triggers:
  - trigger: numeric_state
    entity_id: sensor.cycle_tracker_days_until_period
    above: 0
    below: 1
conditions: []
actions:
  - action: persistent_notification.create
    data:
      title: Cycle Tracker
      message: >-
        Period expected on {{ states('sensor.cycle_tracker_next_period_date') }}.
        You are on cycle day {{ states('sensor.cycle_tracker_cycle_day') }}
        ({{ states('sensor.cycle_tracker_cycle_phase') }} phase).
mode: single
```

## Privacy

Cycle Tracker has no external dependencies and makes no network requests. Period history and settings are written to Home Assistant's own storage (`.storage/cycle_tracker_data` inside your configuration directory) and never leave the instance. The integration declares `iot_class: local_polling` because its only data source is that local storage; it does not collect or transmit any telemetry.

## Development

Development requires **CPython 3.13+** on the Home Assistant **2026.1.0** baseline (the dev toolchain pins `homeassistant==2026.1.0` through `pytest-homeassistant-custom-component==0.13.305` in `requirements-dev.txt`):

```bash
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -r requirements-dev.txt
```

The test suite is currently being rebuilt from the roadmap specifications; the previous unit suite was removed and is preserved in git history. Until tests return, `pre-commit run --all-files` (`ruff`, `ruff-format`, `mypy`) is the local quality gate.

The GitHub Actions workflow in `.github/workflows/` runs the pre-commit hooks on every push and pull request, and a separate workflow runs the HACS and Hassfest validators.

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 skrzypu.
