# Design

## Context

See `proposal.md` — Why. Current state that shapes the approach:

- `custom_components/cycle_tracker/` contains `__init__.py`, `coordinator.py`,
  `sensor.py`, `calendar.py`, `config_flow.py`, `services.py`, `const.py`,
  `manifest.json`, `strings.json`, and `translations/`. There are no frontend
  assets and no `www/` directory.
- `async_setup_entry` in `__init__.py` creates the coordinator, forwards
  platforms, registers services, and registers their teardown. `async_setup`
  does not exist yet.
- `manifest.json` declares `"dependencies": []`, `"requirements": []`,
  `iot_class: local_polling`, and `homeassistant: 2026.1.0`.
- Seven sensors exist: cycle day, cycle phase, next period date, next ovulation
  date, days until period, days until ovulation, and statistics. Entity IDs
  follow the `sensor.cycle_tracker_*` convention because entities are named
  "Cycle Tracker …" without `has_entity_name`.
- Services `cycle_tracker.log_start` and `cycle_tracker.log_end` accept an ISO
  `date` field; `log_end` rejects the call when no period is open.
- The test suite was removed by project decision (2026-11-05), so verification
  for this change is manual plus the existing OpenSpec/HACS/hassfest checks.
- The distribution constraint is one HACS Integration entry
  (`docs/bdr/0002-lovelace-card-ships-with-integration.md`).

## Goals / Non-Goals

**Goals:**

- A single-file Lovelace card that logs period start and end in one tap and
  shows the cycle state without opening Developer Tools.
- Zero build step, zero runtime dependencies, no CDN or external request.
- The integration serves and registers the card automatically, idempotently, and
  without breaking setup when Lovelace is not in storage mode.
- Accessible and theme-aware rendering that follows Home Assistant light and
  dark themes.

**Non-Goals:**

- A visual card editor; the card is configured in YAML in this change.
- Localization of card labels; the first version uses English strings inline.
- Flow-intensity selection in the card; the service keeps the optional field,
  but the card sends only the date.
- Logging a period for a past or future date from the card.
- Editing or deleting recorded periods from the card.
- A "period is open" entity; the card surfaces the service rejection instead.
- A separate HACS Dashboard repository or a second HACS entry.

## Decisions

**1. One ES module, no build step, no external imports.**
`custom_components/cycle_tracker/www/cycle-tracker-card.js` is a plain
`HTMLElement` subclass with a shadow root that renders `ha-card` and native
elements. It does not import Lit, htm, or anything from a CDN. Rationale: the
project is local-only (ADR-0001); a CDN import would add a network dependency
and break offline installs, and a bundler would add tooling the repository does
not otherwise need. Alternatives rejected: Lit plus a bundler (build complexity
for one card), CDN import (privacy and offline regression).

**2. Static path registered once in `async_setup`.**
Register `/cycle_tracker/cycle-tracker-card.js` with
`hass.http.async_register_static_paths` and a `StaticPathConfig` pointing at
`Path(__file__).parent / "www" / "cycle-tracker-card.js"`, guarded so repeated
setup does not register it twice. Add `"http"` to `manifest.json` dependencies
so the HTTP server exists before setup runs. Use `cache_headers=True` because
the resource URL is versioned. Alternative rejected: registering the path per
config entry (duplicate registration and teardown complexity).

**3. Lovelace resource upsert, not blind create.**
On `EVENT_HOMEASSISTANT_STARTED` (or immediately when Home Assistant is already
running), look up the Lovelace resources collection in `hass.data["lovelace"]`.
If Lovelace is absent or not in storage mode, skip silently and log at debug
level. Otherwise compare existing resources by URL prefix and update the
`?v=` parameter when the version changed, or create the item when none exists.
Rationale: config entries can reload, and Home Assistant restarts on every
upgrade; a blind create would accumulate duplicate resources. Alternative
rejected: creating unconditionally at setup (duplicates) and requiring manual
resource setup (worse first-run experience).

**4. Resource cleanup follows the last entry.**
Implement `async_remove_entry` and delete the resource only when no other config
entry for `cycle_tracker` remains. Rationale: the resource is per integration,
not per entry; deleting it while another entry is active would break the card.

**5. Explicit entity map with conventional defaults.**
The card accepts `entities.cycle_day`, `entities.cycle_phase`,
`entities.next_period`, `entities.days_until_period`, and
`entities.days_until_ovulation`, defaulting to
`sensor.cycle_tracker_cycle_day`, `sensor.cycle_tracker_cycle_phase`,
`sensor.cycle_tracker_next_period_date`, `sensor.cycle_tracker_days_until_period`,
and `sensor.cycle_tracker_days_until_ovulation`. Rationale: the frontend has no
stable, public way to resolve sibling entities by device, and explicit IDs are
deterministic and debuggable. Alternative rejected: device-based auto-discovery
through the frontend registry (fragile, depends on internal structures).

**6. Actions call the existing services with the local date.**
The card computes today's date from the browser's local calendar fields and
formats it as `YYYY-MM-DD`; it does not use `toISOString`, which would shift the
date near midnight in non-UTC time zones. Start calls `log_start` directly; end
toggles the button into a confirmation state for five seconds and calls
`log_end` only on the second activation. Rationale: ending a period is not
reversible from the UI, and native dialogs are discouraged in Home Assistant.
Alternative rejected: `window.confirm` (blocking and off-theme).

**7. Errors are rendered, not thrown.**
A failed service call is caught, its message is extracted, and the message is
shown in an `aria-live="polite"` status region while the rendered values stay
visible. A missing entity renders a per-row "not tracked" state instead of
throwing. Rationale: a dashboard card must not break the whole view because one
entity is missing or a service rejects a call.

**8. Card-picker metadata without a preview.**
Push `{ type: "cycle-tracker-card", name: "Cycle Tracker Card", description,
preview: false }` into `window.customCards`. `preview: false` is required
because the card needs a configured `hass` state to render meaningfully.

**9. Styling uses theme variables only.**
Spacing, typography, and colors come from `--ha-card-*`, `--primary-text-color`,
`--secondary-text-color`, `--divider-color`, `--primary-color`, and
`--error-color`. No hard-coded palette, so light and dark themes work without a
reload. Layout is a responsive two-column grid that collapses to one column
below roughly 360 px.

**10. No automated frontend tests in this change.**
The project has no frontend test harness and the Python suite was removed by
decision. Verification is a documented manual checklist on a live Home
Assistant, plus `openspec validate`, `hassfest`, and the HACS validation action.
A JS test harness is a separate decision, not a hidden dependency of this card.

## Risks / Trade-offs

- **Lovelace resource API drift across Home Assistant versions** → access the
  collection defensively, skip on any unexpected shape, log at debug, and keep
  the manual YAML resource documented in the README.
- **Resource duplicates after upgrades or reloads** → upsert by URL prefix and
  assert a single item in the manual checklist.
- **Card and integration drift** → the card ships in the same release and reads
  only entity states and services that already exist; the version query
  parameter makes the served file match the release.
- **End action on no open period** → the service already rejects it; the card
  displays the rejection instead of pretending success.
- **No automated regression coverage** → the manual checklist covers first run,
  restart, YAML mode, missing entity, service error, keyboard use, and both
  themes; automated coverage is deferred with the rest of the test suite.
- **Stale cached card after an update** → the `?v=` parameter changes with the
  manifest version; releases must bump the version.

## Migration Plan

1. Ship the change; no data migration and no schema change.
2. On the first Home Assistant restart after the update, the integration serves
   the card and creates the Lovelace resource.
3. Existing dashboards are untouched; users add the card from the picker.
4. Rollback: remove the card file, the static path registration, and the
   resource; entities and stored cycle data are unaffected.

## Open Questions

- Should a later iteration show flow-intensity selection or a "period open"
  indicator? Both need either a new entity or extra card state and are deferred.
- Is a JS test harness worth adding for cards, given the Python suite was
  removed? Deferred; does not change this design.
