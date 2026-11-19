# Tasks

## 1. Period-open signal (backend)

- [x] 1.1 Add `period_open: bool` to the frozen `Snapshot` in `custom_components/cycle_tracker/domain/prediction.py` and derive it in `build_snapshot` as "any recorded period whose `end` is `None`"; verify with new pytest cases in `tests/domain/test_snapshot.py` covering open, all closed, and no periods, run via `pytest -q`
- [x] 1.2 Add `custom_components/cycle_tracker/binary_sensor.py` exposing a "Cycle Tracker Period Open" binary sensor with the same device info and unique-ID pattern as the sensors, reading `snapshot.period_open` and mirroring coordinator availability, and add `Platform.BINARY_SENSOR` to `PLATFORMS` in `const.py`; verify with a pytest platform test that the state is on/off per the snapshot and unavailable when the coordinator is unavailable, plus a test asserting the entity ID `binary_sensor.cycle_tracker_period_open`
- [x] 1.3 Add pytest e2e coverage that `log_start` turns the sensor on and `log_end` turns it off after the next data update; verify `pytest -q` passes with the new tests included
- [x] 1.4 Run `pre-commit run --all-files`; verify ruff, ruff-format, mypy, and pytest all pass with the new platform and snapshot field

## 2. Card asset (frontend, no JS harness — manual verification)

- [x] 2.1 Create `custom_components/cycle_tracker/www/cycle-tracker-card.js` as a `CycleTrackerCard extends HTMLElement` class with a shadow root, `ha-card` as the root element, and `customElements.define("cycle-tracker-card", …)`; verify with grep that the file contains no `import`/`export` statements and loads in a browser without a console error
- [x] 2.2 Implement `setConfig` with `title` (default "Cycle Tracker"), the eight `entities` keys with conventional defaults, and `show_actions` (default `true`); verify on a live dashboard that a minimal config and an override config both resolve to the expected entity IDs
- [x] 2.3 Implement `set hass` rendering of the stat card: cycle day and days-until-period as two equally dominant headline values, phase row with Polish name and fixed plain-language description, and next period / next ovulation date rows labeled with the "przewidywany/a" suffix; verify on a live dashboard that rendered values match the entity states and the phase descriptions match the fixed mapping from `design.md`
- [x] 2.4 Render statistics (average cycle length, average period length, tracked cycle count, prediction confidence) inside a native `<details>`/`<summary>` disclosure labeled "Statystyki", closed by default; verify on a live dashboard that the disclosure starts closed, expands on activation, and shows a not-tracked state when the statistics entity is missing
- [x] 2.5 Implement the start action ("Rozpocznij okres") calling `cycle_tracker.log_start` with the browser's local date in `YYYY-MM-DD` (local calendar fields, never `toISOString`), disabled while the period-open entity is on; verify manually that the date matches the browser's local day around midnight in a non-UTC time zone and that the button is disabled while a period is open
- [x] 2.6 Implement the end action ("Zakończ okres") with a five-second inline confirmation before calling `cycle_tracker.log_end`, disabled while the period-open entity is off; verify manually that a single activation does not call the service, a second activation does, and the button is disabled while no period is open
- [x] 2.7 Disable both buttons while a service call is in flight, catch service errors, and render the message in an `aria-live="polite"` status region; verify manually that a rejected `log_end` keeps the values visible and shows the message
- [x] 2.8 Register the card in `window.customCards` with type, name, description, and `preview: false`; verify the picker lists "Cycle Tracker Card" and adding it yields a card without a broken preview
- [x] 2.9 Style with Home Assistant theme variables only (no hard-coded colors), a responsive layout that collapses below roughly 360 px, visible focus, and `prefers-reduced-motion` handling; verify manually in light and dark themes and with keyboard-only operation
- [x] 2.10 Open the browser console on a dashboard with the card; verify no errors and no network request outside the Home Assistant origin

## 3. Integration wiring (backend)

- [x] 3.1 Add `async_setup` to `custom_components/cycle_tracker/__init__.py` that registers `/cycle_tracker/cycle-tracker-card.js` through `hass.http.async_register_static_paths` with a `StaticPathConfig`, guarded against double registration, with `cache_headers=True`; verify with a pytest test that a GET of the URL returns the module with a JavaScript content type, using the Home Assistant test client
- [x] 3.2 Add `"http"` to `dependencies` in `custom_components/cycle_tracker/manifest.json`; verify `hassfest` reports no manifest error
- [x] 3.3 Implement the Lovelace resource upsert on `EVENT_HOMEASSISTANT_STARTED` (and immediately when Home Assistant is already running): skip when Lovelace is absent or not in storage mode, update the `?v=` query when the URL matches, otherwise create the item; verify with a pytest test over a fake resources collection that two starts yield one resource with the updated version, plus a manual restart check on a live instance
- [x] 3.4 Implement `async_remove_entry` that deletes the resource only when no other `cycle_tracker` entry remains; verify with pytest that deleting one entry among two keeps the resource and deleting the last entry removes it
- [x] 3.5 Append `?v=<manifest version>` to the resource URL from the loaded manifest; verify with a pytest assertion that the query matches `manifest.json` after a version bump
- [x] 3.6 Run `pre-commit run --all-files`; verify ruff, ruff-format, mypy, and pytest all pass with the new wiring

## 4. Config flow translations

- [x] 4.1 Add `custom_components/cycle_tracker/translations/pl.json` with Polish translations for every key in `strings.json` (all steps, errors, options, selector options, and issues); verify with a pytest key-parity test asserting `strings.json`, `translations/en.json`, and `translations/pl.json` expose identical key sets
- [x] 4.2 Clarify the English copy in `strings.json` and `translations/en.json`, especially the `sheet` step (plain-language guidance for spreadsheet ID, worksheet name, and service-account key file path); verify with the same key-parity test and a manual read-through of the sheet step
- [x] 4.3 Run `hassfest`; verify the new translation file passes validation and no translation error is reported
- [x] 4.4 Run `pre-commit run --all-files`; verify ruff, ruff-format, mypy, and pytest all pass

## 5. Repository hygiene and documentation

- [x] 5.1 Add `*.csv`, `service_account*.json`, and `service-account*.json` to `.gitignore`; verify with `git check-ignore -v` on sample files matching each pattern
- [x] 5.2 Add a "Lovelace card" section to `README.md` with the card YAML, the entity override keys, the action behavior and its gating, and the YAML-mode manual resource fallback; verify every documented key exists in `setConfig` by cross-checking the README against the card source
- [x] 5.3 Confirm the card ships inside the integration directory and no second HACS entry or package is introduced; verify `hacs.json` is unchanged and the asset path is under `custom_components/cycle_tracker/www/`
- [x] 5.4 Bump the manifest version and note the card, the binary sensor, and the Polish config flow in the release description; verify the tag matches `manifest.json` and the served URL carries the same version

## 6. Integration checks

- [x] 6.1 Run `openspec validate add-lovelace-card --strict`; verify it reports no errors
- [x] 6.2 Run `hassfest`; verify it passes with the new dependency, the new platform, and the new translation file
- [ ] 6.3 Run the HACS validation action; verify it passes for the integration category with the bundled asset
  - Adnotacja: HACS validation action passed 10/10 checks for the integration category, but ran against remote `main` (local working tree is uncommitted); the action does not inspect `www/*` assets, so full evidence requires a push + re-run.
- [x] 6.4 Run `pre-commit run --all-files`; verify the full gate (ruff, ruff-format, mypy, pytest) passes cleanly
- [x] 6.5 On a live Home Assistant: install the release, restart, open a dashboard, and add the card from the picker; verify the three dominant values (cycle day with its start-date caption, days until period, confidence with its band), phase description, dates, and statistics disclosure match the entities and both actions work with correct gating
- [x] 6.6 On a live Home Assistant: reload the integration and restart Home Assistant; verify the Lovelace resource count for the card URL stays at one
- [x] 6.7 On a live Home Assistant in YAML-mode Lovelace: verify setup succeeds without a resource and the documented manual resource entry renders the card
- [x] 6.8 On a live Home Assistant with Polish as the language: open the config flow and options flow; verify every step, field, and issue renders in Polish with no raw keys

## 7. Card revision: cycle start date + confidence headline

- [x] 7.1 Add `cycle_start: date | None` to the frozen `Snapshot` in `custom_components/cycle_tracker/domain/prediction.py`, derived in `build_snapshot` as the most recent recorded period start on or before today; verify with pytest cases in `tests/domain/test_snapshot.py` (active cycle → date, no period → None)
- [x] 7.2 Add a `sensor.cycle_tracker_cycle_start_date` DATE sensor in `custom_components/cycle_tracker/sensor.py` (name "Cycle Tracker Cycle Start Date", unique_id `cycle_start_date`, same device info) reading `snapshot.cycle_start`; verify with a pytest platform test in `tests/adapters/test_sensors.py`
- [x] 7.3 In the card, add the `cycle_start` entity key (default `sensor.cycle_tracker_cycle_start_date`) and render an `od <date>` caption under the `Dzień cyklu` headline
- [x] 7.4 In the card, promote prediction confidence to a third dominant headline: whole percentage + Polish band name (`niska`/`średnia`/`wysoka` from `confidence_band`), and drop confidence from the statistics disclosure
- [x] 7.5 Update `README.md` (entities table + Lovelace card section) for the new sensor and the three-headline layout
- [x] 7.6 Update the OpenDesign prototype to the three-headline layout with the cycle-start caption and confidence band
- [x] 7.7 Run `openspec validate add-lovelace-card --strict` and `pre-commit run --all-files`; verify the full gate passes
- [x] 7.8 During live verification: map an HTTP 400 from the Sheets API to a dedicated `invalid_range` error with actionable tab-name/ID guidance, and move the sheet-step account hint out of hardcoded English into the three translation files; verify with the new `test_sheet_step_maps_http_400_to_invalid_range` and the translation key-parity test

## 8. Bundled dashboard (sidebar entry)

- [x] 8.1 Add `custom_components/cycle_tracker/dashboard.py` that creates one storage-mode Lovelace dashboard (`Cykl`, `mdi:calendar-heart`, sidebar) at a hyphenated URL path via the registered `lovelace/dashboards/create` WS command, seeded with a single view `{"type": "custom:cycle-tracker-card"}`, guarded by an ownership marker Store; never overwrites an existing dashboard and never re-creates one the user deleted
- [x] 8.2 Wire dashboard creation into `async_setup` and `async_setup_entry` (and one delayed retry when Lovelace is not ready), and removal into `async_remove_entry` (delete only when the saved config still equals the seeded view and the marker is present); all failures logged, none failing setup
- [x] 8.3 Bump `manifest.json` to `0.2.1` and declare the Lovelace/frontend ordering (implemented as `after_dependencies: ["frontend", "lovelace"]` with `dependencies: ["http"]`, so a minimal configuration is not forced to load the frontend and the one-shot retry covers late setup)
- [x] 8.4 Add pytest coverage in `tests/adapters/test_dashboard.py` for: create-once idempotency, no-op when a dashboard/panel exists, user-deletion marker respected, edited dashboard kept on removal, unmodified dashboard removed with the last entry, not-ready signalling, and exception containment
- [x] 8.5 Update `README.md` with the bundled dashboard section (sidebar entry, URL path, removal semantics) and the `0.2.1` version placeholder
- [x] 8.6 Run `openspec validate add-lovelace-card --strict` and `pre-commit run --all-files`; verify the full gate passes (9/9 hooks, 273 tests)

## 9. Live-verification fixes

- [x] 9.1 During live verification the card rendered `brak danych` for every value while the entities had states: their IDs had been prefixed with an area name (`sensor.prywatne_cycle_tracker_cycle_day`). Make the card resolve a missing default ID by a same-domain suffix match (shortest, then alphabetical), with explicit `entities` overrides still winning; verify on the live dashboard and bump the manifest so the served file changes
- [x] 9.2 During live verification the Lovelace resource kept the previous `?v=` value after the version bump instead of being updated by the upsert; cause: Home Assistant 2026.11 renamed `LovelaceData.mode` to `resource_mode`, so the old attribute read returned `None` and the wiring skipped silently. Read `resource_mode` first with a `mode` fallback, log the reason at INFO, and cover it with `test_upsert_reads_the_renamed_resource_mode`

## 10. Live-verification fixes, second round

- [x] 10.1 During live verification the card showed a predicted ovulation date in the past (`next_ovulation_date` equals the running cycle's centre, which sits fourteen days before the next period). Keep the running cycle's windows for phase derivation, add `Prediction.next_ovulation` computed by advancing with the predicted cycle length to the first ovulation centre on or after the reference date, and make the `next_ovulation_date` sensor, its window attributes and `days_until_ovulation` read it. Cover with `test_days_until_ovulation_skips_to_the_next_cycle_once_this_one_has_passed`, the late-period E2E case and the updated sensor test
- [x] 10.2 Remove the magic entity-ID guessing from the card: bind by `device_id` through the entity registry, resolved from a human-readable device picker in a new visual editor (`getConfigElement`/`getStubConfig`) that lists Cycle Tracker devices as `name — area`; match a bound entity by its conventional ID suffix and then by its stable `unique_id` suffix so a rename cannot break it; auto-bind when exactly one device exists and show a Polish message instead of guessing when several do; keep explicit `entities:` overrides winning; seed the bundled dashboard with one bound card per device (single-person install keeps one card titled `Cykl`, multi-person titles each card with the device name) and record the seeded view in the marker so removal compares against what was actually written
- [x] 10.3 Re-run the full gate and rebuild the package for the next live verification (9/9 hooks, 276 tests, `openspec validate --strict`)
