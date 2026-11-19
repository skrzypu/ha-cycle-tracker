# Design

## Context

See `proposal.md` — Why. Current state that shapes the approach:

- `custom_components/cycle_tracker/` contains `__init__.py`, `coordinator.py`,
  `sensor.py` (seven sensors), `calendar.py`, `services.py` (`log_start` /
  `log_end`), `config_flow.py` (steps: user → preferences → notifications →
  sheet → import offer), `sheets.py`, `repository.py`, `domain/` (models,
  prediction, validation, windows, …), `const.py`, `manifest.json`,
  `strings.json`, and `translations/en.json`. There are no frontend assets and
  no `www/` directory.
- `async_setup_entry` in `__init__.py` creates the coordinator, forwards
  platforms, and registers services. `async_setup` does not exist yet.
- `manifest.json` declares `"dependencies": []`; entities are named
  "Cycle Tracker …" without `has_entity_name`, so IDs follow the
  `sensor.cycle_tracker_*` / `binary_sensor.cycle_tracker_*` convention, all
  grouped under one "Cycle Tracker" device.
- `domain/prediction.py` builds a frozen `Snapshot`
  (`reference_date`, `prediction`, `cycle_day`, `phase`, `statistics`,
  `events`) from the recorded periods; `phase_at()` is the single phase
  source, and only the MENSTRUAL phase is observation-based — the other three
  derive from the predicted next period.
- Services accept an ISO `date` field; `log_end` rejects when no period is
  open, and `log_start` dedups only same-day starts.
- The distribution constraint is one HACS Integration entry
  (`docs/bdr/0002-lovelace-card-ships-with-integration.md`).
- A full pytest suite exists under `tests/` (domain, adapters, e2e, imports),
  and the project gate is `pre-commit run --all-files` (ruff, ruff-format,
  mypy, pytest). There is no JavaScript test harness.

## Goals / Non-Goals

**Goals:**

- A single-file Lovelace card that logs period start and end in one tap and
  shows the cycle state in Polish without opening Developer Tools.
- A stat card: cycle day and days-until-period equally dominant, phase with a
  plain-language description, next period and next ovulation dates, statistics
  in a collapsible disclosure.
- A backend signal (`binary_sensor.cycle_tracker_period_open`) so both action
  buttons are safe: the card disables start while a period is open and end
  while nothing is open.
- Zero build step, zero runtime dependencies, no CDN or external request.
- The integration serves and registers the card automatically, idempotently,
  and without breaking setup when Lovelace is not in storage mode.
- Polish-first config flow via `translations/pl.json`, with clearer English
  fallback copy.
- Accessible and theme-aware rendering that follows Home Assistant light and
  dark themes.

**Non-Goals:**

- CSV import of periods.
- Flow-intensity selection in the card; the service keeps the optional field,
  but the card sends only the date.
- Editing or deleting recorded periods from the card.
- Localization beyond Polish; the English card and a full i18n scheme are
  deferred to idea I-010.
- A visual card editor; the card is configured in YAML in this change.
- A separate HACS Dashboard repository or a second HACS entry.
- A JavaScript test harness; backend changes get pytest tests, the card gets a
  documented manual checklist.

## Decisions

**1. One ES module, no build step, no external imports.**
`custom_components/cycle_tracker/www/cycle-tracker-card.js` is a plain
`HTMLElement` subclass with a shadow root that renders `ha-card` and native
elements. It does not import Lit, htm, or anything from a CDN. Rationale: the
project is local-only (ADR-0001); a CDN import would add a network dependency
and break offline installs, and a bundler would add tooling the repository does
not otherwise need. Alternatives rejected: Lit plus a bundler (build
complexity for one card), CDN import (privacy and offline regression).

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

**5. Stat-card layout with three dominant values and Polish content.**
Direction A: the card leads with three side-by-side headline numbers of equal
visual weight — `Dzień cyklu` (with the cycle start date as an `od <date>`
caption beneath it), `Do okresu`, and `Pewność prognozy` (the prediction
confidence) — because together they answer the everyday "where am I" and "how
sure is this" questions at a glance. Below them: the phase row (`Faza:` + Polish
phase name + one-line plain-language description), then date rows labeled
`Następny okres (przewidywany)` and `Następna owulacja (przewidywana)` — the
"(przewidywany/a)" suffix surfaces the nuance that only the menstrual phase is
observation-based while the other phases and both dates derive from the
predicted next period. Then the action buttons, then the Statistics
disclosure. Labels, action labels, and status messages are Polish in this
iteration; the phase descriptions are the fixed mapping:

- menstrual → `miesiączka` — "dni krwawienia — to, co logujesz jako „okres"
  (od 1. dnia, przez 5 dni, domyślnie 5)"
- follicular → `folikularna` — "po krwawieniu, przed owulacją; organizm
  przygotowuje się do owulacji"
- ovulatory → `owulacyjna` — "okno płodne, wokół owulacji (środek 14 dni przed
  następnym okresem, ±2 dni)"
- luteal → `lutealna` — "po owulacji do następnego okresu"

The `period_length` reference in the menstrual description renders the
configured default (5) because the card cannot read integration config;
exposing the configured length is deferred.

The prediction confidence is the third dominant headline: the statistics
sensor's `prediction_confidence` attribute (0–1) rendered as a whole
percentage, with its `confidence_band` name beneath it in Polish — `niska`
(low, < 0.4), `średnia` (medium, 0.4–0.7), `wysoka` (high, > 0.7), per
BDR-0004. The cycle start date is the most recent recorded period start on or
before today, exposed by a new `sensor.cycle_tracker_cycle_start_date` (DATE)
and shown as an `od <date>` caption under `Dzień cyklu`.

**6. Explicit entity map with conventional defaults.**
The card accepts `entities` keys `cycle_day`, `cycle_start`, `cycle_phase`,
`next_period`, `next_ovulation`, `days_until_period`, `days_until_ovulation`,
`statistics`, and `period_open`, defaulting to `sensor.cycle_tracker_cycle_day`,
`sensor.cycle_tracker_cycle_start_date`, `sensor.cycle_tracker_cycle_phase`,
`sensor.cycle_tracker_next_period_date`,
`sensor.cycle_tracker_next_ovulation_date`,
`sensor.cycle_tracker_days_until_period`,
`sensor.cycle_tracker_days_until_ovulation`,
`sensor.cycle_tracker_statistics`, and
`binary_sensor.cycle_tracker_period_open`. Rationale: the frontend has no
stable, public way to resolve sibling entities by device, and explicit IDs are
deterministic and debuggable. Alternative rejected: device-based
auto-discovery through the frontend registry (fragile, depends on internal
structures).

**7. Actions call the existing services with the browser-local date.**
The card computes today's date from the browser's local calendar fields and
formats it as `YYYY-MM-DD`; it does not use `toISOString`, which would shift
the date near midnight in non-UTC time zones. Start calls `log_start` once;
end toggles the button into a confirmation state for five seconds and calls
`log_end` only on the second activation. Rationale: ending a period is not
reversible from the UI, and native dialogs are discouraged in Home Assistant.
Alternative rejected: `window.confirm` (blocking and off-theme).

**8. Both actions are gated by the period-open binary sensor.**
The start button is disabled while `period_open` is on (a prior open period
would otherwise get an overlapping row appended), and the end button is
disabled while it is off (the service would reject the call). The card reads
the state of the `period_open` entity — this is the entire reason the backend
signal exists. Gating is advisory, not a replacement for validation: the
services keep their own checks as the backstop against stale state.

**9. Errors are rendered, not thrown.**
A failed service call is caught, its message is extracted, and the message is
shown in an `aria-live="polite"` status region while the rendered values stay
visible. A missing entity renders a per-row "not tracked" state instead of
throwing. Rationale: a dashboard card must not break the whole view because one
entity is missing or a service rejects a call.

**10. Card-picker metadata without a preview.**
Push `{ type: "cycle-tracker-card", name: "Cycle Tracker Card", description,
preview: false }` into `window.customCards`. `preview: false` is required
because the card needs a configured `hass` state to render meaningfully.

**11. Statistics in a native disclosure, not tabs.**
The remaining statistics (average cycle length, average period length, tracked
cycle count — read from the statistics sensor's attributes) live in a
`<details>`/`<summary>` disclosure labeled `Statystyki`, closed by default so
the stat card stays scannable; prediction confidence is promoted to a dominant
headline (decision 5), not hidden in the disclosure. Tabs were rejected as visually heavy
for one card and harder to keep accessible. The disclosure is natively
keyboard-operable and needs no JavaScript state.

**12. Period-open is a binary sensor entity, not an attribute.**
`period_open: bool` is added to the frozen `Snapshot` in
`domain/prediction.py`, derived in `build_snapshot` from the recorded periods
alone (`any(period.end is None for period in periods)`), so it is independent
of prediction availability. A new `binary_sensor` platform
(`custom_components/cycle_tracker/binary_sensor.py`) exposes
`binary_sensor.cycle_tracker_period_open` on the existing "Cycle Tracker"
device, mirroring the coordinator availability state like the sensors do.
Rationale for entity over attribute: an entity is first-class in Home
Assistant (state history, templates, automations), and the card already reads
states only. An attribute on the statistics sensor was rejected because it
would be invisible to state-only consumers and harder to template.

**13. Config flow Polish via `pl.json`, clarified English fallback.**
Add `custom_components/cycle_tracker/translations/pl.json` covering every key
in `strings.json` (steps, errors, options, selectors, issues) in Polish —
Polish-first, because that is the primary user. At the same time, clarify the
English copy in `strings.json` and `translations/en.json`, especially the
`sheet` step: plain-language guidance for the spreadsheet ID, worksheet name,
and service-account key file path. English remains the fallback for
unsupported languages. Broader i18n (including an English/l10n card) is
deferred to idea I-010 and not specced here.

**14. Testing: pytest for the backend, a manual checklist for the card.**
Every backend change lands pytest tests: `period_open` derivation in
`tests/domain`, the binary sensor platform, static-path serving, and the
Lovelace resource upsert/removal helpers. The earlier parked draft claimed the
Python suite was removed; that is no longer true, and this design does not
repeat it. The JavaScript card still has no harness, so its verification is a
documented manual checklist on a live Home Assistant plus `hassfest` and the
HACS validation action. A JS test harness remains a separate decision, not a
hidden dependency of this card.

**15. Bundled dashboard via the in-process `lovelace/dashboards/create` WS command.**
Home Assistant offers no public Python/service API for creating a storage
dashboard, so the integration drives the same command the frontend uses. The
dashboard is created at a stable hyphenated URL path (`cykl-miesieczny`), titled
`Cykl` with `mdi:calendar-heart` and shown in the sidebar, and seeded with a
single view holding `{"type": "custom:cycle-tracker-card"}`. An ownership marker
in a dedicated `Store` records that the integration created it, which enables
three safety guarantees: a dashboard the user already had is never touched, a
dashboard the user deleted is never re-created, and the dashboard is only
removed on uninstall while still unmodified. The WS handler is looked up from
`hass.data["websocket_api"]` and called with a minimal stub connection; the
entire call is wrapped so that any future API drift degrades to a logged warning
rather than a setup failure. A YAML-mode Lovelace or a `url_already_exists`
conflict leaves the existing dashboard untouched.

**16. Two ovulation positions: the running cycle's and the next one ahead.**
`Prediction` keeps `ovulation`, `ovulation_center` and `fertile` for the cycle
running at the reference date, because phase derivation needs exactly that
cycle's geometry. For most of the luteal phase those dates are in the past, so
the prediction also carries `next_ovulation: CycleWindows`, produced by walking
forward with the predicted cycle length until the ovulation centre is on or
after the reference date. The `next_ovulation_date` sensor, its window
attributes and `days_until_ovulation` read that field. Rationale: a headline
labelled "następna owulacja" must not show a past date, and clamping the
countdown to zero discards the useful information. Alternatives rejected:
overwriting the current-cycle windows (phase derivation would drift),
clamping the countdown (the behaviour that caused the live defect).

**17. Card binds to a device, not to entity-ID strings.**
The card accepts `device_id` and resolves its nine entities from the entity
registry (through `hass.devices`/`hass.entities`, with the registry websocket
commands as a fallback), matching the conventional ID suffix first and the
stable `unique_id` suffix second, so a rename cannot blank the card. A visual
editor lists Cycle Tracker devices as `name — area` and writes `device_id`, so
nobody types an entity ID; `getStubConfig` returns `{}` so the first drop on a
dashboard auto-binds when there is exactly one device. With several devices and
no choice the card shows a Polish instruction instead of guessing. The bundled
dashboard seeds one bound card per device (title `Cykl` for one person, the
device name for several) and records the seeded view in the ownership marker, so
"unmodified" on removal means "still what we wrote". Rationale: the live defect
came from an entity ID gaining an area prefix, and a household with two people
makes any suffix guess ambiguous. Alternatives rejected: `entry_id` option
(still an opaque string), per-person dashboards (the user asked for one
dashboard with several cards).

## Risks / Trade-offs

- **Lovelace resource API drift across Home Assistant versions** → access the
  collection defensively, skip on any unexpected shape, log at debug, and keep
  the manual YAML resource documented in the README.
- **Resource duplicates after upgrades or reloads** → upsert by URL prefix and
  assert a single item in the manual checklist.
- **Card and integration drift** → the card ships in the same release and reads
  only entity states and services that already exist; the version query
  parameter makes the served file match the release.
- **Stale `period_open` state between a log and the next refresh** → the button
  gating is advisory; the services' own validation remains the backstop, and
  both buttons are disabled while a call is in flight.
- **Binary sensor adds one more entity to the device** → negligible cost; it
  enables the card's safety gating and is independently useful in templates
  and automations.
- **`pl.json` drifting out of sync with `strings.json`** → a pytest key-parity
  test asserts all three files expose the same keys; `hassfest` validates the
  JSON. Broken strings degrade to keys only in unsupported languages.
- **No automated frontend regression coverage** → the manual checklist covers
  first run, restart, YAML mode, missing entity, service error, keyboard use,
  both themes, the three dominant values, and the cycle-start caption;
  automated coverage stays deferred.
- **Stale cached card after an update** → the `?v=` parameter changes with the
  manifest version; releases must bump the version.
- **Bundled-dashboard creation relies on an internal WS registry** → the handler
  is resolved defensively from `hass.data["websocket_api"]`, the call is fully
  wrapped, and any drift degrades to a logged warning; the manual card-picker
  path in the README remains the fallback.
- **The next-ovulation walk could, in principle, loop** → it is bounded to 24
  cycles, and a predicted length so short that the centre never moves forward
  degrades to the last computed window instead of hanging.

## Migration Plan

1. Ship the change; no data migration and no schema change.
2. On the first Home Assistant restart after the update, the binary sensor
   appears on the existing device, the integration serves the card, and the
   Lovelace resource is created on start.
3. Polish-language Home Assistant instances see the Polish config flow
   automatically; other languages keep the English fallback.
4. Existing dashboards are untouched; users add the card from the picker, or use
   the bundled `Cykl` dashboard created in the sidebar.
5. Rollback: remove the card file, the static path registration, the resource,
   the dashboard, the binary sensor platform, and `pl.json`; entities and
   stored cycle data are unaffected.

## Open Questions

- Should a later iteration expose the configured period length to the card so
  the menstrual description can render the real value instead of the default?
  Deferred; the card cannot read integration config today.
- Is a JavaScript test harness worth adding for cards, given a pytest suite
  already gates the backend? Deferred; does not change this design.
- Card i18n beyond Polish (labels per HA language, including English) belongs
  to idea I-010 and is out of scope here.
