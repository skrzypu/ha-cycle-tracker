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

For a full explanation of how prediction works — the phases, the prediction
windows, and what confidence means — see the
[user guide](docs/guide/algorithms.md).

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

## Development tooling

Two opt-in MCP servers are configured in `opencode.json` for debugging against a
live Home Assistant instance and previewing the Lovelace card in OpenDesign. Both
entries are `disabled: true` by default and are turned on only for a specific
session.

> **Data-exposure warning.** Enabling the Home Assistant MCP server sends entity
> states, attributes, history, and logs to the model provider. Home Assistant's
> Read-only mode limits writes, not exposure. Keep the entry disabled unless you
> are actively debugging.

### Home Assistant MCP (read-only)

Rationale: [ADR-0002](docs/adr/0002-read-only-ha-mcp-development-tooling.md),
[ADR-0008](docs/adr/0008-home-assistant-mcp-read-only-core-version.md).

1. In Home Assistant, create an administrator **long-lived access token**:
   **Profile → Security → Long-lived access tokens → Create token**.
2. Store the token outside the repository:
   ```bash
   mkdir -p ~/.secrets && chmod 700 ~/.secrets
   printf '%s' 'YOUR_TOKEN' > ~/.secrets/ha_mcp_token
   chmod 600 ~/.secrets/ha_mcp_token
   ```
   The config references it via `{file:~/.secrets/ha_mcp_token}`, so the token
   value itself never enters `opencode.json`.
3. Add the **Model Context Protocol** integration (the menu entries below only
   appear after this). Either:
   - **Settings → System → AI** → select **Enable** on the **Model Context
     Protocol** card, or
   - **Settings → Devices & services → Add Integration → Model Context
     Protocol** and follow the setup.
   Then copy the **Main URL** (`/api/mcp`). Requires Home Assistant 2025.2+.
4. Enable **Read-only**: **Settings → Devices & services → Model Context
   Protocol → Configure → Read-only** on. (The Read-only option requires
   Home Assistant 2026.10 or newer.)

Verify the token and endpoint — substitute `<HA_HOST>` with your Home Assistant
address (it must match `mcp.servers.homeassistant.url`, which uses the same
placeholder):

```bash
curl -fsS -H "Authorization: Bearer $(cat ~/.secrets/ha_mcp_token)" http://<HA_HOST>:8123/api/
```

To enable it for a debugging session, replace `<HA_HOST>` in
`mcp.servers.homeassistant.url` with your instance's address, set `"disabled":
false`, and restart opencode; set it back to `true` when done.

### OpenDesign (Docker)

Rationale: [ADR-0007](docs/adr/0007-opendesign-mcp-explicit-daemon-url.md)
(supersedes ADR-0003).

1. Install Docker Engine (Ubuntu/WSL: `sudo apt-get install -y docker.io`), add
   your user to the `docker` group, then log out and back in.
2. Start the container. The named volume `open-design-data` is mounted at the
   container's data directory `/app/.od`, and the daemon listens on port `7456`:
   ```bash
   docker run -d --name open-design --restart unless-stopped \
     -p 127.0.0.1:7456:7456 \
     -v open-design-data:/app/.od \
     -e OD_BIND_HOST=0.0.0.0 \
     -e OD_DISABLE_API_AUTH=1 \
     ghcr.io/nexu-io/od:latest
   ```
3. Verify the web surface: `curl -fsS http://127.0.0.1:7456/` returns success.

The MCP server is a stdio process reached through `docker exec`. It must pass
`--daemon-url http://127.0.0.1:7456` explicitly, because daemon auto-discovery
does not work through `docker exec`; this is already set in
`mcp.servers.opendesign`.

To enable it for a session, set `"disabled": false` on `mcp.servers.opendesign`
and restart opencode.

The `opendesign` MCP server exposes 22 tools:
- **Read** (12): `list_projects`, `get_active_context`, `get_artifact`,
  `get_project`, `get_file`, `search_files`, `list_files`, `list_skills`,
  `list_plugins`, `list_agents`, `get_run`, `get_vela_login_status`.
- **Write** (8): `collect_brief`, `confirm_brief`, `create_artifact`,
  `write_file`, `create_project`, `start_run`, `cancel_run`, `start_vela_login`.
- **Destructive** (2, denied by the `opendesign_delete_*` permission rule):
  `delete_file`, `delete_project`.

### Secrets hygiene

- The token lives at `~/.secrets/ha_mcp_token` (outside the repository, mode
  `600`). To rotate it, create a new token in Home Assistant, overwrite the
  file, and re-verify with the `curl` command above.
- Run `git grep -n "Bearer "` to confirm no token value is committed; only the
  `{file:~/.secrets/ha_mcp_token}` reference should appear.

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 skrzypu.
