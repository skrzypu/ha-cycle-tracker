# Proposal

## Why

Roadmap Phase 1 calls for a dedicated Lovelace card so a period start or end can
be logged in one tap, but the repository ships no UI at all: the archived
`python-only-hacs-readiness` change explicitly excluded the card. Without it,
every logging action requires the Developer Tools service dialog or an
automation, which makes the integration impractical for daily use.

## What Changes

- Add a custom Lovelace card, used as `type: custom:cycle-tracker-card`, shipped
  as a single dependency-free ES module at
  `custom_components/cycle_tracker/www/cycle-tracker-card.js`.
- The integration serves the card from a stable URL and creates or updates the
  Lovelace resource idempotently, so users do not add the resource by hand; the
  resource is removed when the config entry is deleted.
- The card shows current cycle day, phase, next period date, next ovulation
  date, and the day counts, and calls `cycle_tracker.log_start` /
  `cycle_tracker.log_end` with today's local date.
- The card registers itself in `window.customCards`, so it appears in the
  "Add card" picker.
- Document card usage and the YAML-mode resource fallback in `README.md`.
- No breaking changes: the card is additive, and existing entities, services,
  and stored data are unchanged.

## Capabilities

### New Capabilities

- `lovelace-card`: the card's user-visible behavior and its delivery — card
  configuration schema, rendered values, logging actions, empty and error
  states, Lovelace resource registration performed by the integration, and
  card-picker metadata.

### Modified Capabilities

- `hacs-distribution`: the distributed package now contains a frontend asset,
  so one HACS Integration entry must deliver and version the card together with
  the Python integration.

## Impact

- **New files**: `custom_components/cycle_tracker/www/cycle-tracker-card.js`,
  `openspec/changes/archive/2026-11-19-add-lovelace-card/specs/lovelace-card/spec.md`, a delta spec
  for `hacs-distribution`.
- **Modified files**: `custom_components/cycle_tracker/__init__.py` (static path
  and Lovelace resource registration), `custom_components/cycle_tracker/manifest.json`
  (`http` dependency), `README.md` (card usage).
- **Unchanged**: coordinator, sensors, calendar, services, config flow, storage
  schema, and prediction algorithms.
- **Dependencies**: none. The card is plain JavaScript with no build step and no
  external imports.
- **Distribution**: still one HACS custom repository, still one release per
  version; no separate HACS Dashboard entry.
