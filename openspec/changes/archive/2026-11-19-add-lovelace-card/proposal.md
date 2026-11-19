# Proposal

## Why

Roadmap Phase 1 calls for a dedicated Lovelace card so a period start or end
can be logged in one tap, but the repository ships no UI at all. Today every
logging action requires the Developer Tools service dialog or an automation,
which makes the integration impractical for daily use.

The card cannot be built safely without one missing backend signal: whether a
period is currently open. Without it, "start" can append an overlapping open
row when a period was started on an earlier day, and "end" just gets rejected
when nothing is open. This change therefore adds that signal first
(`binary_sensor.cycle_tracker_period_open`).

Finally, the config flow is English-only while the primary user wants Polish
first, so this change also adds Polish config-flow strings and clarifies the
English copy, especially the Google Sheets step.

## What Changes

- Add a custom Lovelace card, used as `type: custom:cycle-tracker-card`, shipped
  as a single dependency-free ES module at
  `custom_components/cycle_tracker/www/cycle-tracker-card.js`. The integration
  serves the card from a stable versioned URL and creates or updates the
  Lovelace resource idempotently, so the card appears in the card picker
  without manual resource setup; the resource is removed when the last config
  entry is deleted.
- The card is a stat card in Polish: cycle day and days-until-period as two
  equally dominant headline values, the phase name with a one-line
  plain-language description, the next period and next ovulation dates, cycle
  statistics in a collapsible "Statistics" disclosure, and start/end actions
  that call `cycle_tracker.log_start` / `cycle_tracker.log_end` with the
  browser's local date. The card reads entity states only and never writes
  storage directly.
- Add a `binary_sensor.cycle_tracker_period_open` entity derived as "any
  recorded period with no end date", exposed as `period_open` in the
  coordinator snapshot. The card uses it to disable the unsafe action button
  (start while open, end while closed).
- Add `custom_components/cycle_tracker/translations/pl.json` (Polish-first
  config flow) and clarify the English config-flow copy; English remains the
  fallback via `strings.json` and `translations/en.json`.
- Document card usage and the YAML-mode resource fallback in `README.md`, and
  ignore CSV and service-account key files in `.gitignore`.
- No breaking changes: the card and the binary sensor are additive, and
  existing entities, services, and stored data are unchanged.

## Capabilities

### New Capabilities

- `lovelace-card`: the card's user-visible behavior and its delivery — card
  configuration schema, stat-card layout and Polish content, collapsible
  statistics, logging actions and their safety gating, degraded states,
  Lovelace resource registration performed by the integration, and
  card-picker metadata.

### Modified Capabilities

- `cycle-tracking`: adds the period-open signal — a binary sensor and a
  `period_open` snapshot field derived from recorded periods — so consumers
  can tell whether a period is currently open.
- `hacs-distribution`: the distributed package now contains a frontend asset,
  so one HACS Integration entry must deliver and version the card together
  with the Python integration, and the config-flow strings requirement gains a
  Polish translation with clarified English fallback copy.

## Impact

- **New files**: `custom_components/cycle_tracker/www/cycle-tracker-card.js`,
  `custom_components/cycle_tracker/binary_sensor.py`,
  `custom_components/cycle_tracker/translations/pl.json`, and the OpenSpec
  artifacts for this change (a `lovelace-card` spec plus deltas for
  `cycle-tracking` and `hacs-distribution`).
- **Modified files**: `custom_components/cycle_tracker/__init__.py` (static
  path, Lovelace resource registration and removal),
  `custom_components/cycle_tracker/manifest.json` (`http` dependency),
  `custom_components/cycle_tracker/const.py` (binary sensor platform),
  `custom_components/cycle_tracker/domain/prediction.py` (`period_open` in the
  snapshot), `custom_components/cycle_tracker/strings.json` and
  `translations/en.json` (clarified English copy), `README.md` (card usage),
  `.gitignore` (CSV and service-account files), and pytest tests under
  `tests/` for the backend changes.
- **Unchanged**: calendar, service schemas, storage schema, prediction
  algorithms, and the seven existing sensors.
- **Dependencies**: none new. The card is plain JavaScript with no build step
  and no external imports; the manifest only gains the built-in `http`
  dependency for the static path.
- **Distribution**: still one HACS custom repository, still one release per
  version; no separate HACS Dashboard entry.
- **Testing**: backend changes land pytest tests (suite exists under
  `tests/`, gate is `pre-commit run --all-files`); the JavaScript card has no
  test harness and is verified with a documented manual checklist plus
  `hassfest` and the HACS validation action.
