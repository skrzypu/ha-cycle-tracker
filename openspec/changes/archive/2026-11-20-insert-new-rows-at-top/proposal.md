# Proposal: Insert new rows at top of the Google Sheet

## Why

When Google Sheets is the source of truth (ADR-0004), `log_start` appends new
periods at the bottom of the table, so the current cycle sinks below a growing
block of old rows and scrolls out of view. The stakeholder reads history
newest-first and has clarified the workflow: **row 2 is the current period** —
she types the new date there, edits end date/flow/notes in that same row, and
inserts a blank row above row 2 herself when a new period begins. I-014 was
decided on 2026-11-20; this change implements that decision.

## What Changes

- Add a single `SheetsClient.insert_row` call that first resolves the worksheet
  name to a numeric `sheetId` via `spreadsheets.get`, then uses
  `spreadsheets.batchUpdate` with an `insertDimension` request (a properly nested
  `DimensionRange`) at index 1 (row 2, directly below the header). The header
  stays first.
- Change `SheetsPeriodRepository.upsert` so a **new** `period_id` inserts a row
  directly below the header, while an **existing** `period_id` is updated in
  place. If row 2 is blank, write into it instead of inserting another row. No
  one-time migration of existing sheets: old rows keep their order and new rows
  go above the block.
- Flip the duplicate-`period_id` tie-break in `domain/validation.py` from
  "greater row number wins" to "smaller row number wins" when neither row has
  `updated_at`, because the top row is now the newer one.
- Make `read_all` and `sheet_has_data_rows` skip fully blank rows. This is
  required, not cosmetic: `services.py` requests an immediate refresh after
  every write, so if `insertDimension` succeeds but the follow-up `update_row`
  fails, an empty row 2 must not be reported as an invalid row.
- Update the `sheet-sync` spec requirement "Write period start" from SHALL
  append a row to SHALL insert a new row directly below the header, and align
  the related validation/blank-row behavior.

Explicit non-goals: no second tab and no sorted/formula view (the manual path
is one row insert per cycle); no migration of existing sheets; card, entity
attributes, calendar and prediction stay unaffected because
`validate_period_rows` sorts by `start_date` and sheet row order is
presentational only. ADR-0004 already covers the sheet as source of truth, not
row order, so no ADR is amended. The known I-007 residual (a manual sheet entry
followed by a same-date card Start before the next read can duplicate a start
date) is recorded, not fixed here.

## Capabilities

### New Capabilities

None — this changes behavior within an existing capability.

### Modified Capabilities

- `sheet-sync`: change the "Write period start" requirement from appending a
  row to inserting a new row directly below the header (row 2), writing into a
  blank row 2 instead of inserting a duplicate, and updating existing
  `period_id`s in place. Align row validation so the duplicate-`period_id`
  tie-break favors the smaller row number and fully blank rows are ignored.

## Impact

- `custom_components/cycle_tracker/sheets.py` — new `insert_row` method backed
  by a `spreadsheets.get` sheetId lookup plus `spreadsheets.batchUpdate` /
  `insertDimension`.
- `custom_components/cycle_tracker/repository.py` — `upsert` chooses
  insert-at-row-2 vs. in-place update vs. blank-row-2 fill; `read_all` and
  `sheet_has_data_rows` skip fully blank rows.
- `custom_components/cycle_tracker/domain/validation.py` — duplicate tie-break
  direction and its documentation.
- Tests under `tests/adapters/` (`test_sheets.py`, `test_sheets_repository.py`)
  and `tests/domain/` (`test_validation.py`, `test_sheet_validation.py`).
- Spec delta: `openspec/specs/sheet-sync/spec.md` (change "Write period start"
  and related validation behavior).
