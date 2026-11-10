# Design

## Context

See `proposal.md` — Why. Current state that shapes the approach:

- `coordinator.py` loads a single `Store` document (`cycle_tracker_data`), keeps
  `periods` as a list of `{start_date, end_date, ...}`, and derives predictions,
  phases, and statistics from it. `_async_update_data` currently only reads that
  store; the update interval is six hours.
- `services.py` mutates the coordinator's in-memory data and saves it back to the
  store. `log_start` and `log_end` are registered per config entry.
- `config_flow.py` has `user`, `preferences`, and `notifications` steps and an
  options flow; there is no credential or sheet step.
- `manifest.json` has `requirements: []`; `cryptography` and `aiohttp` are part
  of the Home Assistant runtime, so no new requirement is needed.
- ADR-0004 records the decision; ADR-0001 is superseded; BDR-0003 records the
  product promise.
- The card and the sensors read coordinator data only, so they need no change.

## Goals / Non-Goals

**Goals:**

- The Google Sheet is authoritative for period rows; Home Assistant never keeps a
  competing copy.
- Configuration is validated against the real sheet before an entry is created.
- A missing or broken sheet produces actionable repair issues, not silent
  failures or local fallback writes.
- Existing local periods can be imported once.
- No new Python dependencies.

**Non-Goals:**

- Two-way event sync with conflict resolution beyond last-write-wins per row.
- Creating the spreadsheet from the integration (the service account has no
  Drive storage quota and cannot own files).
- OAuth as an alternative auth model.
- Supporting multiple sheets per config entry.
- Google Form support; rows created by a form are readable if they satisfy the
  schema, but no form is shipped or documented as a supported path.
- Real-time push updates; polling is the only refresh mechanism.
- Encrypting cell contents; the sheet is plaintext to Google by decision.

## Decisions

**1. Direct Google Sheets REST calls with a service account.**
`sheets.py` signs a JWT with the service account's private key using
`cryptography`, exchanges it at `https://oauth2.googleapis.com/token` for an
access token, caches the token until 60 seconds before expiry, and calls the
Sheets v4 REST API through `async_get_clientsession(hass)`. No `gspread`, no
`google-api-python-client`, no new manifest requirement. Alternative rejected:
adding a Google SDK (larger dependency surface for four endpoints).

**2. Store the key path, not the key.**
The config entry stores `service_account_file` as a path relative to the Home
Assistant configuration directory. The path is resolved and must stay inside
`hass.config.config_dir`; anything else is rejected. Rationale: avoids copying
the private key into `.storage/core.config_entries` as a second copy, and blocks
arbitrary file reads through the config flow. The file itself still lives in the
config directory and therefore in backups, which are encrypted by default; the
README documents this.

**3. The user owns the sheet; the service account is a guest.**
The user creates the spreadsheet and shares it with the service account's
`client_email` as Editor. The config flow shows that address after parsing the
key. Rationale: a service account cannot create files in a user's Drive (no
storage quota), and sharing keeps the blast radius to one sheet.

**4. Schema is mapped by header name.**
Row 1 is the header. Required columns: `period_id`, `start_date`, `end_date`,
`flow_intensity`, `notes`, `updated_at`, `source`. Extra columns are ignored;
missing columns fail validation with a list. Rationale: users reorder and add
columns in Sheets; position-based mapping would corrupt data.

**5. Dates are written with `RAW` and read with `UNFORMATTED_VALUE`.**
Writing with `RAW` prevents Sheets from turning ISO strings into serial numbers
or evaluating content as formulas. Reading with `UNFORMATTED_VALUE` returns either
a string (text cell) or a number (date cell); a numeric value is converted from
the Sheets epoch (1899-12-30). Rationale: users will type dates directly, and
Sheets will store those as serials. Any value that is neither an ISO date nor a
serial number is an invalid row.

**6. One row per period, identified by `period_id`.**
`log_start` generates a UUID before the request, appends a row with an empty
`end_date`, and on an ambiguous failure re-reads column A and reuses the row if
the identifier already exists. `log_end` reads column A to locate the latest row
with an empty `end_date` and updates only `end_date` and `updated_at` through
`values:batchUpdate`, leaving flow and notes untouched. Rationale: append has no
idempotency key, and a full-row rewrite would clobber concurrent user edits.

**7. The coordinator is read-through with a cached snapshot.**
`_async_update_data` calls the sheets client, validates rows, and writes the
result to the `Store` cache together with `last_sync`, `last_error`, and
`consecutive_failures`. On failure it returns the cached snapshot instead of
raising, increments the failure counter, and the entities become unavailable when
the counter reaches three. Rationale: a dashboard should keep showing the last
known cycle instead of going blank because Google hiccuped, but it must not
pretend the data is current.

**8. Validation excludes rows, never the sheet.**
Rows are parsed and sorted by start date. A row is excluded and reported when the
start date is missing or unparsable, the end date precedes the start, the range
overlaps an earlier valid row, or the `period_id` duplicates a newer row.
Predictions and statistics use only valid rows. Rationale: one bad row typed on a
phone must not take the integration down.

**9. Repair issues mirror failure classes.**
Five issues: `sheet_not_configured` (persistent), `sheet_auth_failed` (fixable
through reconfiguration), `sheet_unreachable`, `sheet_schema_invalid` (fixable),
and `sheet_rows_invalid` (lists row numbers). Issues are created on the failing
refresh and deleted on the next success of the same class. Rationale: the user
needs to know whether to fix credentials, the sheet name, the header, or a row.

**10. Configuration validates before it saves.**
The `sheet` step parses the key, obtains a token, reads the header row, and
checks the required columns. Errors are `invalid_auth`, `sheet_not_found`,
`invalid_schema`, and `cannot_connect`, each rendered from `strings.json`. The
options flow exposes the same fields plus the poll interval. Rationale: saving an
entry that cannot work only moves the failure to runtime.

**11. Polling defaults to five minutes.**
The interval is configurable from 1 to 60 minutes; the default is five. Writes
request an immediate refresh. Rationale: five minutes keeps phone edits visible
without approaching the Sheets quota of 60 reads per minute per user. The
previous six-hour interval is removed.

**12. Import is offered only into an empty sheet.**
During the `sheet` step, if the worksheet has no data rows and the cache holds
periods, the flow offers a one-time import. Each cached period becomes a row with
a generated `period_id`. If the sheet has data, no import is offered and the
sheet wins. Rationale: the first migration must not silently discard history, and
must never overwrite a sheet the user already populated.

**13. `updated_at` is UTC, period dates are calendar dates.**
`updated_at` is an ISO 8601 UTC timestamp used only for duplicate resolution.
`start_date` and `end_date` are date-only values and are never shifted by a
timezone. Rationale: cycle days are calendar days; converting them through UTC
would move a start date by one day for users east or west of UTC.

**14. No local write fallback.**
When the sheet is unreachable, services raise `HomeAssistantError` with the cause
and the cache stays unchanged. Rationale: a local write would create exactly the
divergence this change exists to remove.

## Risks / Trade-offs

- **Google can read the data** → accepted and recorded in ADR-0004; the README
  states it plainly. Users who need confidentiality must not use this feature.
- **Service account key leakage** → the key grants access only to the shared
  sheet; the path is restricted to the config directory; rotation is documented;
  Home Assistant backups are encrypted by default.
- **Quota and rate limits** (300 requests/minute/project, 60/minute/user) → a
  five-minute poll uses one read per interval; writes are single requests; no
  batch loops over rows.
- **No transactions in Sheets** → `log_end` touches only two cells; `log_start`
  re-reads after an ambiguous failure; last-write-wins is documented.
- **Users break the header** → schema validation produces a named repair issue
  instead of a silent stop.
- **Date coercion** → writes use `RAW`; reads accept ISO or serial only; anything
  else is reported.
- **Google outage or no internet** → cache keeps the last snapshot for up to
  three intervals, then entities become unavailable.
- **Workspace sharing policies may block service accounts** → the README
  documents the failure and the fix (allow the service account or use a personal
  account).
- **Large sheets** → reads request only the required columns and a bounded range;
  the sheet is expected to hold one row per period, not telemetry.

## Migration Plan

1. Existing config entries have no sheet settings. On upgrade they create the
   `sheet_not_configured` issue and the entities become unavailable; no data is
   deleted from the local store.
2. The user creates the spreadsheet, shares it with the service account, saves
   the key file in the config directory, and completes the `sheet` step.
3. If the sheet is empty and cached periods exist, the flow offers the one-time
   import; accepting writes every cached period as a row.
4. The first successful read replaces the cache and the repair issues clear.
5. Rollback: restore the previous integration version; the local cache still
   holds the last synced snapshot, so entities render, but edits made only in the
   sheet after the rollback are not visible.

## Open Questions

- Should the default poll interval be five or ten minutes? Five is chosen for
  responsiveness; it can be raised if quota becomes a concern.
- Should a Google Form be documented as a supported entry path? Rows it creates
  can satisfy the schema, but `period_id` and `updated_at` must be filled.
- Should the key file be supported from a path outside the config directory
  (for example a mounted secret) at the cost of the path restriction?
