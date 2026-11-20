# Cycle Tracker

A Home Assistant custom integration for menstrual cycle tracking, with cycle-length prediction calculated locally in pure Python.

## Features

- Current cycle day and cycle phase (`menstrual`, `follicular`, `ovulatory`, `luteal`)
- Predicted next period date with an uncertainty window, and a predicted ovulation center with ovulation and fertile windows
- Countdown sensors for days until the next period and the next ovulation, with an explicit late state
- Cycle statistics over the prediction window: average cycle length, average period length, standard deviations, total recorded periods, and a confidence value with a band
- Calendar entity listing recorded periods plus projected predicted periods, ovulation windows and fertile windows
- Two services to log period start and period end, including flow intensity
- Three selectable prediction algorithms: arithmetic mean, weighted moving average and median
- A Google Sheet you own is the single source of truth, so periods can be entered and edited from anywhere; Home Assistant keeps only a cache of the last successful read

## Requirements

- Home Assistant **2026.1.0** or newer (declared in `custom_components/cycle_tracker/manifest.json` and `hacs.json`)
- HACS, if you want to use the HACS installation path (manual installation works without it)
- A Google Sheet and a Google Cloud service account key (see [Google Sheets setup](#google-sheets-setup))

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

The config flow has four steps:

| Step | Fields |
| --- | --- |
| Cycle settings | `cycle_length` (20–45, default 28), `period_length` (2–10, default 5), `last_period_start` (date) |
| Prediction preferences | `prediction_algorithm` (default `weighted_moving_average`), `notification_offset_days` (0–14, default 2) |
| Notifications | `enable_notifications` (default false), `notification_time` (default `08:00`) |
| Google Sheet | `spreadsheet_id`, `worksheet` (default `Sheet1`), `service_account_file` (path, inside the configuration directory), `poll_interval` (1–60 minutes, default 5) |

The Google Sheet step validates the connection and the header row before the entry is created. If the sheet is empty and you have periods recorded locally, it offers a one-time import of those periods into the sheet.

All settings can be changed afterwards through **Configure** on the integration entry, which exposes cycle length, period length, prediction algorithm, notification offset, the two notification preferences, and the four sheet fields in a single step.

### Prediction

Cycle lengths are derived from the differences between consecutive recorded period start dates.

- Once at least two usable completed cycles exist, the next period is predicted from the most recent six usable cycle lengths, using the algorithm selected in the options.
- Cycles outside the 15–90 day bounds and everything recorded at or before the most recent gap longer than 90 days are excluded from prediction and reported as warnings.
- Below two usable cycles, the prediction sensors report `unknown`; the configured `cycle_length` is not used as a fallback.
- `arithmetic_mean` averages the cycle lengths equally, `weighted_moving_average` weights newer cycles more heavily, and `median` takes the middle value.
- The predicted date comes with an uncertainty window of ±1 standard deviation, never narrower than ±2 days.
- The ovulation center is 14 days before the predicted next period, with a ±2-day ovulation window and a six-day fertile window ending on the center.

Entities are refreshed from the sheet on the configured poll interval (default 5 minutes), and the derived snapshot is rebuilt when the local date changes, so the late flag flips at midnight. If a sync fails, the last successful snapshot is kept for up to three intervals before the entities report unavailable.

For a full explanation of how prediction works — the phases, the prediction
windows, and what confidence means — see the
[user guide](docs/guide/algorithms.md).

## Google Sheets setup

The integration reads and writes a Google Sheet you own through a Google Cloud
**service account**. You create the sheet and share it with the service account;
the integration signs in as the service account and treats the sheet as the
single source of truth.

1. **Create a service account** in the [Google Cloud Console](https://console.cloud.google.com/):
   create (or select) a project, open **IAM & Admin → Service Accounts**, and
   create a service account. Under the new account's **Keys** tab, add a key of
   type **JSON** and download it. Enable the **Google Sheets API** for the
   project (**APIs & Services → Library → Google Sheets API → Enable**).
2. **Place the key** inside your Home Assistant configuration directory, for
   example `<config>/service_account.json`. The integration stores only the path
   to the key, never the key contents, and rejects paths outside the
   configuration directory.
3. **Create the sheet** in [Google Sheets](https://sheets.google.com) and share
   it with the service account's `client_email` (from the downloaded JSON key; it
   ends in `@….iam.gserviceaccount.com`) as **Editor**. Share only this one sheet
   to limit what the key can touch.
4. **Add the header row** as the first row of the worksheet, with exactly these
   columns (order does not matter):
   `period_id`, `start_date`, `end_date`, `flow_intensity`, `notes`, `updated_at`.
5. In the config flow, enter the **spreadsheet ID** (the long identifier in the
   sheet's URL), the **worksheet name**, the **key path**, and the **poll
   interval**.

Rows the integration writes get a `period_id` and an `updated_at` automatically.
If you add rows by hand, give each a unique `period_id` (a UUID) and an
`updated_at` ISO timestamp so duplicate handling and edits keep working; leave
`end_date` empty for a period that is still open.

**Key rotation.** To rotate the key, create a new key for the same service
account in the Cloud Console, overwrite the key file, and restart Home
Assistant, then delete the old key. Because the integration stores only the
path, only the file needs replacing.

**Workspace sharing.** If your Google Workspace organization blocks sharing with
external service accounts, share the sheet with the `client_email` from within
the organization, or use a personal Google account.

## Entities

All entities are grouped under a single **Cycle Tracker** device.

| Entity ID | Friendly name | Description |
| --- | --- | --- |
| `sensor.cycle_tracker_cycle_day` | Cycle Tracker Cycle Day | Elapsed day in the current cycle, which keeps counting past the configured cycle length instead of wrapping |
| `sensor.cycle_tracker_cycle_start_date` | Cycle Tracker Cycle Start Date | Start date of the current cycle (the most recent recorded period start); `unknown` before any period is recorded |
| `sensor.cycle_tracker_cycle_phase` | Cycle Tracker Cycle Phase | `menstrual`, `follicular`, `ovulatory` or `luteal`, derived from the ovulation window; `unknown` without a prediction |
| `sensor.cycle_tracker_next_period_date` | Cycle Tracker Next Period Date | Predicted start date of the next period; `unknown` below two usable completed cycles; attributes: `uncertainty_start`, `uncertainty_end`, `predicted_cycle_length`, `usable_cycle_count` |
| `sensor.cycle_tracker_next_ovulation_date` | Cycle Tracker Next Ovulation Date | Predicted ovulation center; attributes: `ovulation_window_start`, `ovulation_window_end`, `fertile_window_start`, `fertile_window_end` |
| `sensor.cycle_tracker_days_until_period` | Cycle Tracker Days Until Period | Days remaining until the predicted next period, `0` when the period is due or late; attributes: `is_late`, `days_late` |
| `sensor.cycle_tracker_days_until_ovulation` | Cycle Tracker Days Until Ovulation | Days remaining until the predicted ovulation center |
| `sensor.cycle_tracker_statistics` | Cycle Tracker Statistics | Number of recorded periods; attributes: `average_cycle_length`, `average_period_length`, `cycle_length_std_dev`, `period_length_std_dev`, `shortest_cycle`, `longest_cycle`, `total_cycles_tracked`, `prediction_confidence`, `confidence_band`, `usable_cycle_count`, `warnings` |
| `binary_sensor.cycle_tracker_period_open` | Cycle Tracker Period Open | `on` while a recorded period has no end date, `off` otherwise |
| `calendar.menstrual_cycle` | Menstrual Cycle | Recorded periods plus the projected predicted period, ovulation window and fertile window |

Prediction-dependent sensors return an unknown state until at least two usable completed cycles have been recorded. Entity IDs can be renamed from the entity settings, so they are not guaranteed to stay exactly as listed above.

## Services

Both services resolve the configuration entry from the entity or device they are called on, so the action has to be targeted at a Cycle Tracker entity or device. The services write to the configured Google Sheet and raise an error if the sheet is not configured or is unreachable, so a failed call never reports success.

| Service | Field | Required | Type / allowed values | Description |
| --- | --- | --- | --- | --- |
| `cycle_tracker.log_start` | `date` | yes | date (`YYYY-MM-DD`) | Start date of the period |
| `cycle_tracker.log_start` | `flow_intensity` | no | `spotting`, `light`, `medium`, `heavy` (default `medium`) | Intensity of the flow |
| `cycle_tracker.log_end` | `date` | yes | date (`YYYY-MM-DD`) | End date of the period |

Both services return a response object with `success` (boolean) and `message` (string). Logging a period end when no period has been started, or ending a period that was already ended, returns `success: false`.

## Lovelace card

The integration ships a Lovelace card for logging period start and end from a
dashboard and for showing the current cycle state at a glance. The card is
bundled inside the integration directory and served by Home Assistant, so
installing or updating the HACS **Integration** entry is enough — there is no
separate Dashboard repository, package, or resource to add.

Add the card through **Add card → Manual** with this YAML:

```yaml
type: custom:cycle-tracker-card
title: Cycle Tracker   # optional, defaults to "Cycle Tracker"
show_actions: true     # optional, defaults to true
entities:              # optional per-entity overrides
  cycle_day: sensor.cycle_tracker_cycle_day
  cycle_start: sensor.cycle_tracker_cycle_start_date
  cycle_phase: sensor.cycle_tracker_cycle_phase
  next_period: sensor.cycle_tracker_next_period_date
  next_ovulation: sensor.cycle_tracker_next_ovulation_date
  days_until_period: sensor.cycle_tracker_days_until_period
  days_until_ovulation: sensor.cycle_tracker_days_until_ovulation
  statistics: sensor.cycle_tracker_statistics
  period_open: binary_sensor.cycle_tracker_period_open
```

The card has a visual editor: pick the person from the **Urządzenie** list
(each Cycle Tracker device appears as `name — area` when it belongs to an area)
and the card binds to that device, resolving its entities itself. No entity ID
has to be typed. With exactly one Cycle Tracker device the card binds to it
automatically; with several devices and none chosen it shows a Polish message
instead of guessing. An `entities` override still wins for the keys it covers.
Its labels and messages are Polish-language in this release.

Binding is by `device_id`, so renaming an entity does not break the card: it
matches the entity's conventional ID suffix first and its stable internal
`unique_id` suffix otherwise. The old suffix fallback over `hass.states` remains
only for installations where the device registry is unavailable.

### Bundled dashboard

On setup the integration also creates a dashboard titled **Cykl** at
`/cykl-miesieczny`, shown in the sidebar, with one card per Cycle Tracker device
(one person = one entry = one device), ordered by device name. A single-person
install gets one card titled `Cykl`; a multi-person install titles each card with
its device name. Each card carries its own `device_id`. It is created only when
no dashboard or panel already uses that path, and it is never written to again
afterwards — your edits to it are preserved, and a person added later is added as
a card by hand. If you delete the dashboard, it stays deleted (it is not
re-created on later restarts). Removing the integration deletes the dashboard
only while it is still unmodified.

The card leads with three equally prominent values: **Dzień cyklu** (with the
cycle start date as a caption beneath it), **Do okresu** (days until the next
period), and **Pewność prognozy** (prediction confidence as a whole percentage,
with its band `niska` / `średnia` / `wysoka` for low / medium / high). Below them
are the phase, the predicted dates, the action buttons, and a collapsible
**Statystyki** disclosure with the average cycle length, average period length,
and tracked cycle count.

### Card options

| Key | Required | Description |
| --- | --- | --- |
| `type` | yes | Always `custom:cycle-tracker-card`. |
| `title` | no | Card heading; defaults to `Cycle Tracker`. |
| `show_actions` | no | Show the start and end action buttons; defaults to `true`. |
| `device_id` | no | Binds the card to one Cycle Tracker device; set by the visual editor, not typed by hand. |
| `entities` | no | Mapping that overrides the entity ID for any of the nine keys below; omitted keys keep their default. |

| `entities` key | Default entity ID |
| --- | --- |
| `cycle_day` | `sensor.cycle_tracker_cycle_day` |
| `cycle_start` | `sensor.cycle_tracker_cycle_start_date` |
| `cycle_phase` | `sensor.cycle_tracker_cycle_phase` |
| `next_period` | `sensor.cycle_tracker_next_period_date` |
| `next_ovulation` | `sensor.cycle_tracker_next_ovulation_date` |
| `days_until_period` | `sensor.cycle_tracker_days_until_period` |
| `days_until_ovulation` | `sensor.cycle_tracker_days_until_ovulation` |
| `statistics` | `sensor.cycle_tracker_statistics` |
| `period_open` | `binary_sensor.cycle_tracker_period_open` |

### Actions

The two buttons call the existing services with the browser's local date, so
they log the day you see on your own clock:

- **Rozpocznij okres** calls `cycle_tracker.log_start`. It is disabled while a
  period is already open (`period_open` is `on`), because a second start would
  add an overlapping row.
- **Zakończ okres** calls `cycle_tracker.log_end`. It is disabled while no
  period is open (`period_open` is `off`), because the service would reject the
  call. Activating it once asks for confirmation; the service is called only on
  a second activation within five seconds.

Both buttons are disabled while a service call is in flight. A failed call is
shown as a message in the card's status region and the last rendered values stay
visible. The button gating comes from `binary_sensor.cycle_tracker_period_open`;
the services keep their own validation, so stale state cannot corrupt the sheet.

### YAML-mode resource

In storage mode (the Home Assistant default) the integration registers the card
resource automatically. When Lovelace runs in YAML mode, the integration does
not modify your dashboard configuration, so add the resource manually:

```yaml
lovelace:
  mode: yaml
  resources:
    - url: /cycle_tracker/cycle-tracker-card.js?v=0.2.7
      type: module
```

The `v=` value must match the integration version (the `version` field in
`custom_components/cycle_tracker/manifest.json`); bump it when you upgrade so
the browser does not serve a cached copy of the card.

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

Your cycle data is **special-category health data**. The configured Google Sheet
is the single source of truth for recorded periods, so the data is **sent to and
readable by Google** whenever the integration syncs
([ADR-0004](docs/adr/0004-google-sheets-source-of-truth.md)). Home Assistant
keeps only a cache of the last successful read (in `.storage/`), and the
integration makes no other network requests and collects no telemetry.

The service account key is stored only as a path in the config entry; the key
file itself lives in your configuration directory and therefore in your backups
(encrypted by default). The key grants access only to the sheet you share with
it, so share a single sheet with **Editor** access to limit the blast radius,
and rotate the key if it is ever exposed. If you remove the sheet configuration
later, periods that were never written to a sheet are no longer accessible.

## Development

Development requires **CPython 3.13+** on the Home Assistant **2026.1.0** baseline (the dev toolchain pins `homeassistant==2026.1.0` through `pytest-homeassistant-custom-component==0.13.305` in `requirements-dev.txt`):

```bash
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -r requirements-dev.txt
```

`pytest` covers the pure prediction domain (`tests/domain`), the Home Assistant adapters (`tests/adapters`) and the domain import boundary (`tests/imports`). `pre-commit run --all-files` is the local quality gate: `ruff`, `ruff-format`, `mypy` over `custom_components/` against the real Home Assistant types, and the full test suite.

The GitHub Actions workflow in `.github/workflows/` runs the pre-commit hooks on every push and pull request, and a separate workflow runs the HACS and Hassfest validators.

## Development tooling

Test layers and the quality bar for the end-to-end suite are recorded in
[ADR-0012](docs/adr/0012-e2e-tests-verify-shipped-contract.md): E2E tests drive
the public integration surface with literal expectations from the documented
algorithm, and every new or changed E2E test must be shown to fail against a
targeted mutation of the code it covers.

The project uses pinned agent skills from [skills.sh](https://www.skills.sh/),
locked in `skills-lock.json`. Which skills are installed, why, where they are
applied and whether they still earn their place is listed in
[docs/skills/README.md](docs/skills/README.md) — that index, not the individual
`SKILL.md` files, is the review surface
([ADR-0013](docs/adr/0013-agent-skills-pinned-indexed-reviewed.md)).

Two MCP servers are configured in `opencode.json`: Home Assistant for debugging
against a live instance, and OpenDesign for card design work. Both stay
`disabled: true` by default — nothing connects, no tool schemas are loaded, and
no state leaves the machine. Access is already wired per agent in the `mcps`
lists of [`.opencode/oh-my-opencode-slim.json`](.opencode/oh-my-opencode-slim.json),
so enabling one is a single-line change: set `"disabled": false` on
`mcp.servers.<name>` in `opencode.json`, restart opencode, and set it back to
`true` when done.

Once a server is enabled, these agents receive its tools:

| Agent | `homeassistant` | `opendesign` |
| --- | --- | --- |
| `orchestrator` | yes | yes |
| `designer` | yes | yes |
| `oracle` | yes | no |
| `explorer` | yes | no |
| `fixer` | yes | no |
| `librarian` | no | no |
| `observer` | no | no |

An agent whose list omits a server is denied that server's tools by an
agent-level `<server>_*` permission rule generated by the plugin. Custom agents
defined in `.opencode/agent/*.md` are not covered by that mechanism and fall back
to the global rules in `opencode.json`.

> **Data-exposure warning.** While the Home Assistant server is enabled, its
> tools send entity states, attributes, history, and logs to the model provider
> whenever an agent reads them. Home Assistant's Read-only mode limits writes,
> not exposure. Turn the entry off again when the debugging session ends, and
> remove `homeassistant` from an agent's `mcps` list if that agent should never
> see it.

### Home Assistant MCP (read-only)

Rationale: [ADR-0002](docs/adr/0002-read-only-ha-mcp-development-tooling.md),
[ADR-0008](docs/adr/0008-home-assistant-mcp-read-only-core-version.md),
[ADR-0015](docs/adr/0015-mcp-access-pre-wired-per-agent-allowlists.md)
(ADR-0015 keeps "disabled by default" and pre-wires the per-agent allowlists).

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

The URL is `http://{env:HA_MCP_HOST}:8123/api/mcp`, so the address stays out of
the repository. Export it in the shell that starts opencode (and persist it in
your shell profile):

```bash
export HA_MCP_HOST=192.168.1.10
```

Verify the token and endpoint:

```bash
curl -fsS -H "Authorization: Bearer $(cat ~/.secrets/ha_mcp_token)" \
  "http://$HA_MCP_HOST:8123/api/"
```

If `HA_MCP_HOST` is unset, the substitution yields an empty string and opencode
logs `Invalid MCP URL` for the server after you set `"disabled": false`; the rest
of opencode still starts.

### OpenDesign (Docker)

Rationale: [ADR-0007](docs/adr/0007-opendesign-mcp-explicit-daemon-url.md)
(supersedes ADR-0003), and
[ADR-0015](docs/adr/0015-mcp-access-pre-wired-per-agent-allowlists.md)
(keeps "disabled by default" and pre-wires the per-agent allowlists).

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

Enable it with `"disabled": false` on `mcp.servers.opendesign` and restart
opencode; the container must be running (`docker start open-design`), otherwise
opencode logs a failed MCP start and continues. Destructive tools stay removed by
the `opendesign_delete_*` deny rule, so `delete_file` and `delete_project` never
reach an agent.

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
