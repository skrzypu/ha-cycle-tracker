# Tasks

## 1. Card asset

- [ ] 1.1 Create `custom_components/cycle_tracker/www/cycle-tracker-card.js` with a `CycleTrackerCard extends HTMLElement` class, a shadow root, and `ha-card` as the root element; verify the module defines and registers `customElements.define("cycle-tracker-card", CycleTrackerCard)` with no imports
- [ ] 1.2 Implement `setConfig` with `title` (default "Cycle Tracker"), `entities` defaults for the five sensors, and `show_actions` (default `true`); verify a minimal config and an override config both resolve to the expected entity IDs
- [ ] 1.3 Implement `set hass` rendering for cycle day, cycle phase, next period date, next ovulation date, days until period, and days until ovulation; verify each row renders from `hass.states` and that missing, `unavailable`, or `unknown` states render a "not tracked" state
- [ ] 1.4 Implement the start action calling `cycle_tracker.log_start` with today's local date in `YYYY-MM-DD`; verify the date matches the browser's local calendar day around midnight in a non-UTC time zone
- [ ] 1.5 Implement the end action with a five-second inline confirmation before calling `cycle_tracker.log_end`; verify a single activation does not call the service and a second activation does
- [ ] 1.6 Disable both buttons while a call is in flight, catch service errors, and render the message in an `aria-live="polite"` status region; verify a rejected `log_end` keeps the values visible and shows the message
- [ ] 1.7 Register the card in `window.customCards` with type, name, description, and `preview: false`; verify the picker lists "Cycle Tracker Card"
- [ ] 1.8 Style with Home Assistant theme variables only (no hard-coded colors), a responsive grid, visible focus, and `prefers-reduced-motion` handling; verify light and dark themes and keyboard-only operation

## 2. Integration wiring

- [ ] 2.1 Add `async_setup` to `custom_components/cycle_tracker/__init__.py` that registers `/cycle_tracker/cycle-tracker-card.js` through `hass.http.async_register_static_paths` with a `StaticPathConfig`, guarded against double registration; verify a GET of the URL returns the module
- [ ] 2.2 Add `"http"` to `dependencies` in `custom_components/cycle_tracker/manifest.json`; verify `hassfest` reports no manifest error
- [ ] 2.3 Implement the Lovelace resource upsert on `EVENT_HOMEASSISTANT_STARTED` (and immediately when Home Assistant is already running): skip when Lovelace is absent or not in storage mode, update the version query when the URL matches, otherwise create the item; verify one resource exists after two restarts
- [ ] 2.4 Implement `async_remove_entry` that deletes the resource only when no other `cycle_tracker` entry remains; verify deleting a single entry among two keeps the resource, and deleting the last entry removes it
- [ ] 2.5 Append `?v=<manifest version>` to the resource URL; verify the query matches `manifest.json` after a version bump

## 3. Documentation and distribution

- [ ] 3.1 Add a "Lovelace card" section to `README.md` with the card YAML, the entity override keys, the action behavior, and the YAML-mode manual resource fallback; verify every documented key exists in `setConfig`
- [ ] 3.2 Confirm the card ships inside the integration directory and no second HACS entry or package is introduced; verify `hacs.json` is unchanged and the asset path is under `custom_components/cycle_tracker/www/`
- [ ] 3.3 Bump the manifest version and note the card in the release description; verify the tag matches `manifest.json` and the served URL carries the same version

## 4. Verification

- [ ] 4.1 Run `openspec validate add-lovelace-card --strict`; verify it reports no errors
- [ ] 4.2 Run the HACS validation action and `hassfest`; verify both pass with the new dependency and asset
- [ ] 4.3 On a live Home Assistant: install the release, restart, open a dashboard, and add the card from the picker; verify values match the entities and both actions work
- [ ] 4.4 On a live Home Assistant: reload the integration and restart Home Assistant; verify the Lovelace resource count for the card URL stays at one
- [ ] 4.5 On a live Home Assistant in YAML-mode Lovelace: verify setup succeeds without a resource and the documented manual resource entry renders the card
- [ ] 4.6 Open the browser console on a dashboard with the card; verify no errors and no network request outside the Home Assistant origin
