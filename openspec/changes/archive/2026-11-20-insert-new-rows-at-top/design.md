# Design: Insert new rows at top of the Google Sheet

## Context

See `proposal.md` for motivation and `specs/sheet-sync/spec.md` for the behavior
contract. Current state, verified in code:

- `sheets.py` exposes `read_rows`, `append_row`, `update_row`, `clear_row` — all
  against the values API; `append_row` uses `insertDataOption=INSERT_ROWS`, which
  still writes at the bottom of the table. The worksheet is known only by its
  NAME string; `spreadsheets.get` is needed to resolve the numeric `sheetId`
  that `DimensionRange` requires for an insert.
- `repository.py` `SheetsPeriodRepository.upsert` scans rows for the
  `period_id` and calls `update_row` (found) or `append_row` (not found);
  `read_all` maps `rows[1:]` by header name; `sheet_has_data_rows` is
  `len(rows) > 1`.
- `_map_row_to_period` returns `None` for an unparseable `start_date`, so a
  blank row currently becomes an invalid-row report.
- `validation.py` `_is_newer_period` uses "greater row number wins" when
  neither duplicate has `updated_at`.
- `services.py` requests a refresh immediately after `log_start` and after a
  successful `log_end`, so every write is read back from the sheet on the same
  call.
- `coordinator.py` uses `self._periods[-1]` as the latest period, but
  `validate_period_rows` and `_upsert_in_memory` sort by `start_date`; sheet row
  order is presentational only.

ADR-0004 covers the sheet as source of truth, not row order (ADR-0001 is
superseded). The stakeholder workflow is decided: row 2 is the current period.

## Goals / Non-Goals

**Goals:**

- A new `period_id` written by Home Assistant appears directly below the
  header, above the existing block of rows.
- The manual workflow stays viable: a blank row 2 the user inserted is written
  into rather than duplicated, and blank rows do not produce invalid-row noise
  on the immediate post-write refresh.
- Duplicate-`period_id` resolution continues to pick the correct (now topmost)
  row when timestamps are absent.

**Non-Goals:**

- Migrating or reordering existing sheets; no second tab, `QUERY`/`SORT` view or
  pivot.
- Changing card, entity attributes, calendar, prediction, or domain ordering.
- Fixing the I-007 duplicate-start-date residual (manual entry followed by a
  same-date card Start before the next read).
- Amending any ADR.

## Decisions

### 1. New `SheetsClient.insert_row` via `spreadsheets.get` + `spreadsheets.batchUpdate`

The integration knows the worksheet only by NAME, but `InsertDimensionRequest`
requires a numeric `sheetId` inside a `DimensionRange` object. Resolve the id
first with a `GET` to `https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}`
using a field mask `fields=sheets.properties.title,sheets.properties.sheetId`,
matching `sheets[].properties.title == worksheet`. The existing OAuth scope
`https://www.googleapis.com/auth/spreadsheets` already covers this call.

Then POST a `batchUpdate` body with a single `insertDimension` request whose
`range` is a **DimensionRange object** (not a worksheet-name string):

```json
{
  "insertDimension": {
    "range": {
      "sheetId": <numeric id>,
      "dimension": "ROWS",
      "startIndex": 1,
      "endIndex": 2
    },
    "inheritFromBefore": false
  }
}
```

`startIndex = 1`, `endIndex = 2` inserts one row at row 2 (directly below the
header). Reuse the existing token/JSON/error helpers.

- **Recommended approach:** resolve the `sheetId` on every insert. Inserts are
  rare (once per cycle), so the extra GET is cheap and resolving each time
  avoids stale-cache issues if the worksheet is renamed or recreated. Use the
  field mask above to keep the response small. Raise the existing
  `SheetsApiError` when no sheet title matches the configured worksheet or the
  response is malformed (missing/invalid `sheets[].properties`) rather than
  guessing an id. The insert remains a separate call followed by `update_row` —
  the insert-then-write, two-call flow and the behavioral contract (row 2,
  header stays first) are unchanged.
- **Why:** `insertDimension` creates a real row below the header and shifts the
  existing block down, preserving cell values and formatting; it is the only
  listed API call that writes at a chosen position. The `spreadsheets.get`
  lookup is required because `DimensionRange` addresses sheets by numeric id.
- **Alternatives considered:**
  - Reusing `append_row` with `INSERT_ROWS` — rejected; it only appends at the
    bottom, which is the problem being fixed.
  - Reading the whole table and rewriting it one row lower — rejected; much
    larger write surface, loses cell formatting, and risks data loss on partial
    failure.
  - Passing the worksheet name as `range`, or putting `dimension` /
    `startIndex` / `endIndex` at the top level of `insertDimension` — rejected;
    the API requires a `DimensionRange` object with a numeric `sheetId`.
  - Caching the resolved `sheetId` — rejected; inserts are too infrequent to
    justify it, and a cache can go stale after a worksheet rename/recreate.
  - One atomic `batchUpdate` combining `insertDimension` and `updateCells` —
    attractive because it removes the partial-failure window, but it introduces
    a second request-body construction path (and still needs the sheetId
    lookup). Blank-row handling is required anyway for the user's manual blank
    rows, so two calls (`insert_row` then `update_row`) are acceptable here;
    combining them is a safe later refinement.

### 2. `upsert` decision tree

On write:

1. Read rows and validate the header (unchanged).
2. If a row matches the `period_id` → `update_row` at that row (in place).
3. Else if row 2 is blank → `update_row` at row 2.
4. Else → `insert_row` (insert a blank row at index 1), then `update_row` at
   row 2 with the new values.

- **Why:** matches the decided workflow exactly — existing periods are edited
  in place, the current period is always the top row, and the user's manually
  inserted blank row is reused.
- **Insert-then-write:** the new row is inserted blank first because the values
  API addresses a range, so the row must exist before `update_row` can target
  it. Step 4 is the only case with a partial-failure window; the next decision
  contains it.

### 3. Blank-row detection and skipping

Define "fully blank row" as a data row whose mapped cells for all required
columns are empty (empty string or absent). Apply it in:

- `read_all` — skip such rows before validation so they never become
  "missing or unparsable start_date" reports.
- `sheet_has_data_rows` — count only non-blank data rows, so a sheet holding
  just the header and blank rows is still eligible for the one-time import.

A row with *some* content but a blank/invalid `start_date` remains invalid and
must still be reported — only fully blank rows are skipped.

- **Why:** `services.py` refreshes immediately after every write. If
  `insertDimension` succeeds but `update_row` fails, row 2 is left blank; without
  this change the same call would surface a false invalid-row repair issue. It
  also makes the user's manual blank row harmless.

### 4. Flip the duplicate tie-break

In `_is_newer_period`, change the no-timestamp fallback from
`candidate_row > existing_row` to `candidate_row < existing_row`, and update the
`validate_period_rows` docstring accordingly. Keep the `updated_at` rules
unchanged (newest timestamp wins; a timestamp beats no timestamp).

- **Why:** the newest period is now the topmost row, so the smaller row number
  is the newer one. Without the flip, a duplicate without `updated_at` would
  resolve to the older row below it.

### 5. Keep ordering domain-side

No changes to `coordinator.py`, `sensor.py`, `calendar.py`, the card, or
`validate_period_rows`'s final sort. `self._periods[-1]` stays the latest
period by start date.

- **Why:** sheet row order is presentational; sorting by `start_date` makes all
  downstream consumers insensitive to where a row physically sits.

## Risks / Trade-offs

- **[Existing formulas or external tools reference fixed row indices]** →
  `insertDimension` shifts rows down; Sheets adjusts in-sheet A1 references, but
  external scripts with hard-coded indices may need updating. No migration is
  performed; documented as a known limitation of the manual workflow.
- **[Partial failure leaves a blank row 2]** → skipped on read (Decision 3) and
  correctly reported via the existing Sheets API error path; the following
  refresh shows a clean sheet. A later atomic batch is an optional hardening.
- **[Worksheet title cannot be resolved to a sheetId]** → the `spreadsheets.get`
  lookup runs on each insert and raises the existing `SheetsApiError` when no
  `sheets[].properties.title` matches the configured worksheet or the response
  is malformed. No id is cached, so renames/recreates cannot leave a stale id.
- **[One-time import reverses row order in the sheet]** → importing several
  cached periods inserts each new one at row 2, leaving them newest-first in
  the sheet. Harmless because the domain re-sorts by `start_date`; no action.
- **[Concurrent manual sheet edit between read and insert]** → pre-existing
  last-write-wins race, not worsened by this change.
- **[I-007 duplicate start date]** → recorded residual, explicitly out of
  scope.

## Migration Plan

No data migration: existing sheets keep their row order, and the first new
period written after deployment goes above the block at row 2. Rollback is a
code revert only — inserted rows are ordinary valid period rows and need no
undo. Per ADR-0016, archiving this change bumps the patch version in
`custom_components/cycle_tracker/manifest.json` (0.2.8 → 0.2.9).
