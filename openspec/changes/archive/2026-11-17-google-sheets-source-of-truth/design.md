# Design

## Context

See `proposal.md` — Why. Current state that shapes the approach:

- `coordinator.py` loads one `Store` document (`cycle_tracker_data`) and keeps
  `periods` as a list of legacy `{start_date, end_date, flow_intensity}` dicts;
  identity is derived from the start date (`legacy_period_id`). `_async_update_data`
  reads only that store; the update interval is six hours.
- `services.py` mutates the coordinator's in-memory dicts and saves back to the
  store. `log_start` and `log_end` are registered per config entry.
- The domain package (`domain/models.py`, `domain/ports.py`) already holds
  `Period`, `Clock`, and `PredictionConfig`, but there is no `PeriodRepository`
  port and no `period_id` is ever persisted (ADR-0006 defines both).
- `config_flow.py` has `user`, `preferences`, and `notifications` steps; no
  credential or sheet step. `manifest.json` has `requirements: []`;
  `cryptography` and `aiohttp` are in the Home Assistant runtime.
- ADR-0004 records the decision; ADR-0001 is superseded; BDR-0003 records the
  product promise. ADR-0006 fixes the domain model this sheet schema must map
  onto.

## Goals / Non-Goals

**Goals:**

- Storage is swappable: one `PeriodRepository` port, a local adapter first, the
  Google Sheets adapter second (the storage-swap decision).
- The configured Google Sheet is authoritative for period rows; Home Assistant
  never keeps a competing copy.
- Manual edits in the sheet are picked up, validated, and reported.
- Configuration is validated against the real sheet before an entry is created.
- Existing local periods can be imported once.
- No new Python dependencies.

**Non-Goals:**

- Manual correction of periods from Home Assistant (I-007) and a visible
  "invalid rows" tab (I-008) — separate UI changes that depend on the parked
  Lovelace card; captured as ideas, not built here.
- Two-way event sync with conflict resolution beyond last-write-wins per row.
- Creating the spreadsheet from the integration, OAuth as an auth model,
  multiple sheets per entry, Google Forms, real-time push, or cell encryption.

## Decisions

**1. A thin `PeriodRepository` port, cache lives above it.**
`PeriodRepository` exposes `read_all() -> list[Period]`, `upsert(period)`,
`delete(period_id)`. Two adapters implement it: a local `Store` adapter and a
`SheetsPeriodRepository`. Cache, freshness, failure counting, and repair issues
live in the coordinator, above the port, shared by both adapters. Rationale:
satisfies the storage-swap decision and ADR-0005 (SRP, DIP); the cache logic is
written and tested once. Alternative rejected: folding cache/freshness into the
Sheets adapter, which couples them to Google and blocks a clean local adapter.

**2. Migrate to real `period_id` through the local adapter first.**
The local adapter persists `period_id` (UUID) on every row; `legacy_period_id`
is removed once stored ids exist. This is a pure refactor with no user-visible
behavior change and is the foundation the sheet adapter reuses. Rationale: the
sheet adapter needs a stable, editable identity; deriving it from the date
(ADR-0006's `legacy_period_id`) cannot survive a date correction.

**3. Direct Google Sheets REST calls with a service account.**
`sheets.py` signs a JWT with `cryptography`, exchanges it at
`https://oauth2.googleapis.com/token` for an access token (cached until 60
seconds before expiry), and calls the Sheets v4 REST API through
`async_get_clientsession(hass)`. No `gspread`, no `google-api-python-client`.
Alternative rejected: adding a Google SDK for four endpoints.

**4. Store the key path, not the key.**
The config entry stores `service_account_file` as a path that must resolve
inside `hass.config.config_dir`. Rationale: avoids copying the private key into
`.storage/core.config_entries` and blocks arbitrary file reads through the flow.

**5. The user owns the sheet; the service account is a guest.**
The user creates the spreadsheet and shares it with the service account's
`client_email` as Editor; the flow shows that address. Rationale: a service
account cannot create files in a user's Drive, and sharing limits blast radius.

**6. Schema is mapped by header name; no `source` column.**
Row 1 is the header. Required columns: `period_id`, `start_date`, `end_date`,
`flow_intensity`, `notes`, `updated_at`. The adapter maps these onto the domain
`Period` at the boundary. The parked `source` column is dropped: ADR-0006 makes
origin an adapter concern, and duplicate resolution uses `updated_at`, not
`source`. Extra columns are ignored; missing columns fail validation.

**7. Dates are written `RAW`, read `UNFORMATTED_VALUE`.**
`RAW` prevents Sheets from coercing ISO strings; `UNFORMATTED_VALUE` returns a
string or a serial, and serials are converted from the Sheets epoch
(1899-12-30). Anything else is an invalid row.

**8. One row per period, identified by `period_id`.**
`log_start` generates a UUID, appends a row with an empty `end_date`, and on an
ambiguous failure re-reads column A and reuses the row with the same id.
`log_end` locates the latest open row and updates only `end_date` and
`updated_at` through `values:batchUpdate`, leaving flow and notes untouched.

**9. The coordinator is read-through with a cached snapshot.**
`_async_update_data` calls the repository, validates rows, and writes the result
to the `Store` cache with `last_sync`, `last_error`, `consecutive_failures`. On
failure it returns the cached snapshot, increments the counter, and marks
entities unavailable at three failures. Rationale: keep the last cycle visible
through a Google hiccup without pretending it is current.

**10. Validation excludes rows, never the sheet.**
Rows are parsed and sorted by start date. A row is excluded and reported when
its start is missing/unparsable, end precedes start, the range overlaps an
earlier valid row, or `period_id` duplicates a newer row. Predictions use only
valid rows. Rationale: one bad row typed on a phone must not take the
integration down.

**11. Repair issues mirror failure classes.**
Five issues — `sheet_not_configured`, `sheet_auth_failed`, `sheet_unreachable`,
`sheet_schema_invalid`, `sheet_rows_invalid` — created on the failing refresh
and cleared on the next success of the same class. Rationale: the user must know
whether to fix credentials, the sheet name, the header, or a row.

**12. Configuration validates before it saves.**
The `sheet` step parses the key, obtains a token, reads the header, and checks
required columns; errors are `invalid_auth`, `sheet_not_found`,
`invalid_schema`, `cannot_connect`. The options flow exposes the same fields
plus the poll interval.

**13. Polling defaults to five minutes.**
Configurable 1–60 minutes, default five; writes request an immediate refresh.
The previous six-hour interval is removed.

**14. Import is offered only into an empty sheet.**
During the `sheet` step, an empty worksheet plus cached periods offers a
one-time import; a populated sheet wins and no import is offered.

**15. `updated_at` is UTC; period dates are calendar dates.**
`updated_at` is an ISO 8601 UTC timestamp for duplicate resolution; `start_date`
and `end_date` are date-only and never shifted by a timezone.

**16. No local write fallback.**
When the sheet is unreachable, services raise `HomeAssistantError` with the
cause and the cache stays unchanged.

## Risks / Trade-offs

- [Google reads the data (GDPR Article 9)] → accepted and recorded in ADR-0004;
  the README states it plainly.
- [Service account key leakage] → key grants access only to the shared sheet;
  path restricted to the config directory; rotation documented.
- [Quota/rate limits] → five-minute poll is one read per interval; writes are
  single requests; no row loops.
- [No transactions in Sheets] → `log_end` touches two cells; `log_start`
  re-reads after an ambiguous failure; last-write-wins documented.
- [Users break the header] → schema validation raises a named repair issue.
- [Date coercion] → `RAW` on write; ISO-or-serial on read; anything else reported.
- [Google outage / no internet] → cache holds the snapshot up to three
  intervals, then entities become unavailable.
- [Workspace sharing policies block service accounts] → README documents the
  failure and the fix.
- [Over-abstraction] → the port has three operations only; cache/freshness stay
  in the coordinator, not in the port.

## Migration Plan

1. Land the port + local adapter and migrate logging to `period_id` with no
   user-visible change; existing stored dicts gain a `period_id` on first read.
2. Add the sheet adapter, config step, repair issues, and import.
3. Existing entries create `sheet_not_configured` and entities go unavailable;
   no data is deleted from the local store.
4. The user creates the sheet, shares it, saves the key, and completes the
   `sheet` step; an empty sheet plus cached periods offers the one-time import.
5. The first successful read replaces the cache and clears repair issues.
6. Rollback: restore the previous version; the local cache still holds the last
   snapshot, but sheet-only edits made after rollback are not visible.

## Open Questions

- Default poll interval five vs ten minutes (five chosen; raise if quota is a
  concern).
- Whether a Google Form is a supported entry path (its rows can satisfy the
  schema, but `period_id` and `updated_at` must be filled).
- Whether the key file may live outside the config directory (a mounted secret)
  at the cost of the path restriction.
