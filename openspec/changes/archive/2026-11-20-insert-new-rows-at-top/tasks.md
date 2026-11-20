# Tasks

## 1. Sheets client insert API

- [x] 1.1 Add `SheetsClient.insert_row` that resolves the worksheet name to a numeric `sheetId` via a field-masked `spreadsheets.get` (raising `SheetsApiError` on no match or malformed response), then POSTs a `spreadsheets.batchUpdate` body with a single `insertDimension` request whose `range` is a `DimensionRange` object (`sheetId`, `dimension=ROWS`, `startIndex=1`, `endIndex=2`), using the existing token/error helpers; verify `tests/adapters/test_sheets.py` asserts the URLs, auth header, and request bodies and passes.

## 2. Repository write path

- [x] 2.1 Change `SheetsPeriodRepository.upsert` to: update an existing `period_id` in place; if row 2 is blank, write into row 2; otherwise call `insert_row` then `update_row` at row 2; verify `tests/adapters/test_sheets_repository.py` covers all three cases and passes with no `append_row` call remaining in the new-period path.
- [x] 2.2 Cover the partial-failure case (insert succeeds, `update_row` raises) so the error propagates and no duplicate row is created; verify a dedicated test in `tests/adapters/test_sheets_repository.py` passes.

## 3. Blank-row read handling

- [x] 3.1 Skip fully blank data rows in `read_all` before validation so they produce no invalid-row report, while partly filled rows with a missing/invalid `start_date` are still reported; verify `tests/adapters/test_sheets_repository.py` and `tests/domain/test_sheet_validation.py` cover both cases and pass.
- [x] 3.2 Count only non-blank data rows in `sheet_has_data_rows` so a sheet with a header and blank-only rows is treated as empty; verify `tests/adapters/test_sheets_repository.py` and `tests/adapters/test_import.py` cover the blank-only import case and pass.

## 4. Duplicate tie-break direction

- [x] 4.1 Flip `_is_newer_period`'s no-timestamp fallback from greater-row-number-wins to smaller-row-number-wins and update the `validate_period_rows` docstring; verify `tests/domain/test_validation.py` and `tests/domain/test_sheet_validation.py` assert the top row wins and pass, with `updated_at` precedence unchanged.

## 5. Integration and regression checks

- [x] 5.1 Run `pytest tests/adapters/test_sheets.py tests/adapters/test_sheets_repository.py tests/adapters/test_sheets_coordinator_cache.py tests/adapters/test_services.py tests/domain/test_validation.py tests/domain/test_sheet_validation.py` and verify it passes, confirming the immediate post-write refresh sees no invalid-row report after an insert.
- [x] 5.2 Run `pytest tests/adapters/test_calendar.py tests/adapters/test_sensors.py tests/e2e` and verify it passes, confirming card/entity/calendar/prediction ordering is unaffected by sheet row order.

## 6. Release housekeeping

- [x] 6.1 Bump `"version"` in `custom_components/cycle_tracker/manifest.json` from 0.2.8 to 0.2.9 per ADR-0016 during archive and verify the file parses as JSON with the new version.
