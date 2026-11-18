# Proposal

## Why

Cycle data lives only in Home Assistant storage, so it cannot be entered or
edited from a phone outside the home network and is not usable in a spreadsheet.
The user wants a Google Sheet they own as the single source of truth: entry from
Home Assistant at home, editing in the Sheets app from anywhere, and no second
copy that can silently diverge (BDR-0003, ADR-0004). This revives the parked
`google-sheets-source-of-truth` plan, restructured around the storage-swap
decision: introduce a swappable persistence port first, then add the sheet as a
second adapter behind it.

## What Changes

- **Introduce a persistence port** (`PeriodRepository`: read all, upsert,
  delete) and a local `Store`-backed adapter, and migrate `log_start`,
  `log_end`, and refresh to persist `Period` values with a real `period_id`
  (UUID) through the port. No user-visible behavior changes here; it makes the
  storage swappable.
- **Add a Google Sheets adapter** behind the same port; the configured sheet
  becomes the source of truth and Home Assistant storage becomes a cache of the
  last successful snapshot.
- **Manual entry in the sheet**: the sheet is human-editable; reads pick up
  manual edits, validate each row, and exclude-and-report invalid rows instead
  of failing.
- **Configuration gains a sheet step** (spreadsheet ID, worksheet name, service
  account key path, poll interval), validated against the real header row.
- **Repair issues** surface each failure class (not configured, auth failed,
  unreachable, invalid schema, invalid rows).
- **One-time import** of existing local periods into an empty sheet.
- **BREAKING**: local storage is no longer authoritative. A user who removes
  sheet configuration loses access to data never written to a sheet.
- **UI is out of scope**: the Lovelace card, manual period correction in Home
  Assistant (I-007), and an invalid-rows tab (I-008) are deferred. This change
  builds the persistence foundation — the port and its adapters — following
  ADR-0005 (SOLID / Clean Architecture), so storage is swappable and the sheet
  is a backend, not a UI feature.

## Capabilities

### New Capabilities

- `sheet-sync`: the Google Sheets connection and data contract — credentials and
  configuration, header schema, read and write behavior, row validation, cache
  and freshness, and the repair issues shown when configuration or Google is
  unavailable.

### Modified Capabilities

- `cycle-logging-services`: persistence changes from local storage to the
  configured sheet, and the services must fail explicitly when the sheet is not
  configured or unreachable.
- `cycle-tracking`: recorded periods come from the sheet, so period identity and
  duplicate handling are defined by the sheet's stable `period_id` rather than
  by local storage.

## Impact

- **New files**: `custom_components/cycle_tracker/sheets.py` (async Sheets
  client), `custom_components/cycle_tracker/repository.py` (port plus local and
  sheet adapters), `custom_components/cycle_tracker/repairs.py`.
- **Modified files**: `coordinator.py` (read through the repository, cache
  snapshot), `services.py` (write through the repository), `config_flow.py`
  (sheet step), `const.py` (new keys), `strings.json` and `translations/`
  (new steps and repair issues), `README.md` (Google Cloud setup, sharing,
  privacy).
- **Dependencies**: none new — JWT signing uses `cryptography` and HTTP uses
  `aiohttp`, both in the Home Assistant runtime.
- **Privacy**: cycle data is sent to and readable by Google; ADR-0001 is
  superseded by ADR-0004 and the README must state the exposure.
