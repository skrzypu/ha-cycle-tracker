# Tasks

## 1. Google Sheets client

- [ ] 1.1 Create `custom_components/cycle_tracker/sheets.py` with a service-account JWT flow: parse the key file, sign an RS256 assertion with `cryptography`, exchange it at `https://oauth2.googleapis.com/token`, and cache the access token until 60 seconds before expiry; verify a token is reused across two consecutive calls
- [ ] 1.2 Implement `async_read_rows()` against `GET /v4/spreadsheets/{id}/values/{worksheet}` with `UNFORMATTED_VALUE` and the required column range; verify a sheet with one data row returns the header and the row
- [ ] 1.3 Implement `async_append_row()` against `values:append` with `valueInputOption=RAW` and `insertDataOption=INSERT_ROWS`; verify the row lands in the next empty row and ISO dates stay text
- [ ] 1.4 Implement `async_update_cells()` against `values:batchUpdate` for the `end_date` and `updated_at` cells of one row; verify flow and notes are unchanged
- [ ] 1.5 Map HTTP failures to typed errors: 401/403 → auth, 404 → sheet or worksheet not found, 429/5xx/timeout → unreachable; verify each maps to a distinct exception
- [ ] 1.6 Verify no new entry is needed in `manifest.json` (`cryptography` and `aiohttp` come from the Home Assistant runtime) and that the module makes no blocking calls on the event loop

## 2. Configuration flow and strings

- [ ] 2.1 Add constants for `spreadsheet_id`, `worksheet_name`, `service_account_file`, `sync_interval_minutes`, and the default interval (5) to `const.py`; verify imports resolve and no duplicate keys exist
- [ ] 2.2 Add a `sheet` step to `config_flow.py` after the `user` step with the four fields and a description placeholder showing the parsed `client_email`; verify the form renders and the address appears
- [ ] 2.3 Validate the key path resolves inside `hass.config.config_dir` and reject anything else with `invalid_key_path`; verify `../../etc/passwd` is rejected and `cycle_tracker_service_account.json` is accepted
- [ ] 2.4 Validate the connection in the step: parse the key, obtain a token, read the header, and check the required columns; verify errors `invalid_auth`, `sheet_not_found`, `invalid_schema`, and `cannot_connect` each render a translated message
- [ ] 2.5 Extend the options flow with the sheet fields and the poll interval (1–60 minutes); verify a change survives an integration reload
- [ ] 2.6 Add the new step, field labels, error keys, and repair issue texts to `strings.json` and mirror them in `translations/en.json`; verify hassfest reports no mismatch

## 3. Coordinator and cache

- [ ] 3.1 Replace the store-only `_async_update_data` with a read-through: call the sheets client, validate rows, build the period list, and write the snapshot plus `last_sync`, `last_error`, and `consecutive_failures` to the store; verify a successful read replaces the cache
- [ ] 3.2 Implement row validation: parse ISO strings and Sheets serial numbers, sort by start date, and exclude rows with a missing start, end before start, overlap with an earlier valid row, or a duplicate `period_id` resolved by newest `updated_at`; verify each case with a fixture row set
- [ ] 3.3 Keep the cached snapshot on failure instead of raising, increment the failure counter, and expose `last_sync` and `sync_status` as attributes on the statistics sensor; verify a failed refresh leaves values visible
- [ ] 3.4 Mark entities unavailable when `consecutive_failures` reaches 3; verify the transition at the third failure and the recovery on the next success
- [ ] 3.5 Change the update interval to the configured value with a default of five minutes and request an immediate refresh after a successful write; verify the interval is applied after an options change

## 4. Services

- [ ] 4.1 Rewrite `log_start` to generate a `period_id`, append a row with an empty `end_date`, and request a refresh; verify one row appears and the entities update without waiting for the interval
- [ ] 4.2 Handle the same-day open period: if the latest row is open and starts on the requested date, update flow intensity instead of appending; verify the row count does not grow
- [ ] 4.3 Handle an ambiguous append failure by re-reading column A and reusing an existing row with the same `period_id`; verify a simulated timeout followed by a retry produces one row
- [ ] 4.4 Rewrite `log_end` to locate the latest row with an empty `end_date` and update `end_date` and `updated_at` only; verify flow and notes survive the update
- [ ] 4.5 Raise `HomeAssistantError` with a cause-specific message when the sheet is not configured, credentials fail, or Google is unreachable, and make no local write; verify the cache is unchanged after a failed call
- [ ] 4.6 Keep service registration and teardown per config entry; verify both services disappear after unload

## 5. Repairs

- [ ] 5.1 Create `custom_components/cycle_tracker/repairs.py` with issue helpers for `sheet_not_configured`, `sheet_auth_failed`, `sheet_unreachable`, `sheet_schema_invalid`, and `sheet_rows_invalid`; verify each issue has a translation key and a fix hint
- [ ] 5.2 Create `sheet_not_configured` for entries without sheet settings and make it persistent; verify an upgraded entry shows the issue and the entities are unavailable
- [ ] 5.3 Delete an issue on the next successful refresh of the same class; verify fixing the header removes `sheet_schema_invalid` without a restart
- [ ] 5.4 Include row numbers in `sheet_rows_invalid` and keep it updated as rows are fixed; verify the issue text lists the offending rows

## 6. Migration and import

- [ ] 6.1 Offer a one-time import in the `sheet` step when the worksheet has no data rows and the cache holds periods; verify the choice is stored in the entry data
- [ ] 6.2 Write imported periods as rows with generated `period_id` values and UTC `updated_at`; verify the row count equals the cached period count and predictions match the pre-migration values
- [ ] 6.3 Skip the import when the sheet already has data and treat the sheet as authoritative; verify no cached row is written
- [ ] 6.4 Verify an upgraded entry without sheet settings keeps its local cache and shows the configuration issue instead of deleting data

## 7. Documentation

- [ ] 7.1 Document the Google Cloud setup: create a project, enable the Sheets API, create a service account, download the JSON key, and note the `client_email`
- [ ] 7.2 Document sharing the spreadsheet with that address as Editor and the exact header row to create
- [ ] 7.3 Document the privacy statement: Google can read the data, the key lives in the config directory and in encrypted backups, and rotation means a new key plus a restart
- [ ] 7.4 Document troubleshooting for `invalid_auth`, `sheet_not_found`, `invalid_schema`, `cannot_connect`, and Workspace sharing policies that block service accounts
- [ ] 7.5 Cross-link ADR-0004 and BDR-0003 from the README section

## 8. Verification

- [ ] 8.1 Run `openspec validate google-sheets-source-of-truth --strict`; verify it reports no errors
- [ ] 8.2 Run `hassfest` and the HACS validation action; verify both pass
- [ ] 8.3 On a live Home Assistant with a real sheet: complete the flow, log a start, log an end, edit a row in Sheets, and delete a row; verify the entities follow each change within one poll
- [ ] 8.4 Test failure paths: wrong key, unshared sheet, renamed worksheet, removed header column, unparsable date, and no internet; verify each produces the intended repair issue and that fixing it clears the issue
- [ ] 8.5 Verify quota behavior: run ten consecutive refreshes and confirm the token is reused and no request is rate-limited
- [ ] 8.6 Verify no secret is committed: `git grep -n "private_key"` returns nothing and `git status` lists no key file
