# Proposal

## Why

Cycle data currently lives only in Home Assistant storage, so it cannot be read
or edited from a phone that cannot reach Home Assistant, and it is not usable in
a spreadsheet. The user wants a Google Sheet they own to be the single source of
truth: entry from Home Assistant at home, editing in the Sheets app from
anywhere, and no second copy that can silently diverge.

## What Changes

- **A Google Sheet becomes the source of truth** for period records, with one
  row per period: `period_id`, `start_date`, `end_date`, `flow_intensity`,
  `notes`, `updated_at`, `source`.
- **The integration talks to the Google Sheets API directly** using a service
  account JSON key: `log_start` appends a row, `log_end` updates the latest open
  row, and manual edits in the Sheet are picked up on the next poll.
- **Home Assistant storage becomes a cache**, not a database: it keeps the last
  known-good snapshot and sync metadata, so entities can render while a read is
  in flight or failing.
- **Configuration gains a sheet step** (spreadsheet ID, worksheet name, service
  account key path, poll interval) with validation against the real header row,
  plus an options flow to change it later.
- **Missing or broken configuration is surfaced, not hidden**: a repair issue
  with setup instructions, an unavailable state for the entities, and a setup
  hint on the card.
- **Existing local periods can be imported once** into an empty sheet, so
  current users do not lose history.
- **BREAKING**: local storage is no longer authoritative. A user who removes the
  sheet configuration loses access to data that was never written to a sheet.

## Capabilities

### New Capabilities

- `sheet-sync`: the Google Sheets connection and data contract — credentials and
  configuration, header schema, read and write behavior, row validation, cache
  and freshness, and the repair issues shown when configuration or Google is
  unavailable.

### Modified Capabilities

- `cycle-logging-services`: the persistence requirement changes from local
  storage to the configured sheet, and the services must fail explicitly when
  the sheet is not configured or unreachable.
- `cycle-tracking`: recorded periods now come from the sheet, so period identity
  and duplicate handling are defined by the sheet schema rather than by local
  storage.

## Impact

- **New files**: `custom_components/cycle_tracker/sheets.py` (async Google Sheets
  client), `custom_components/cycle_tracker/repairs.py`, sheet spec delta.
- **Modified files**: `coordinator.py` (read through the sheet, cache snapshot),
  `services.py` (write through the sheet), `config_flow.py` (sheet step and
  options), `const.py` (new configuration keys), `strings.json` and
  `translations/en.json` (new steps and repair issues), `manifest.json` (no new
  requirements), `README.md` (Google Cloud setup, sharing, rotation).
- **Unchanged**: prediction algorithms, sensors, calendar, card behavior, HACS
  packaging.
- **Dependencies**: none new. JWT signing uses `cryptography` and HTTP uses
  `aiohttp`, both present in the Home Assistant runtime.
- **Privacy**: cycle data is sent to Google and is readable by Google. ADR-0001
  is superseded by ADR-0004; the README must state the exposure explicitly.
