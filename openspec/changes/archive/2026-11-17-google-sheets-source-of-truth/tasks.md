# Tasks

## 1. Persistence port and local adapter

- [x] 1.1 Add a `PeriodRepository` Protocol (`read_all`, `upsert`, `delete`) to `domain/ports.py` and verify `tests/imports` still passes and the protocol imports cleanly in plain Python.
- [x] 1.2 Add a local `Store`-backed adapter that reads/writes `Period` rows with a persisted `period_id` (UUID), and verify a unit test round-trips a period and preserves its id.
- [x] 1.3 Migrate `log_start`/`log_end` in `services.py` to go through the repository with a real `period_id` instead of mutating legacy dicts, and verify the existing service tests pass plus a new assertion that the id survives a reload.
- [x] 1.4 Migrate the coordinator read path to use the repository and drop the `legacy_period_id` derivation once stored ids exist, and verify the e2e persistence test (`tests/e2e/test_persistence_flow.py`) reproduces the same numbers after a restart.
- [x] 1.5 Add domain-level tests for the adapter's upsert/delete and for the period invariants (overlap, end-before-start), and verify they run without Home Assistant.

## 2. Google Sheets transport

- [x] 2.1 Add `sheets.py` with a service-account JWT flow (parse the key, sign an RS256 assertion with `cryptography`, exchange at `https://oauth2.googleapis.com/token`, cache the token until 60s before expiry) and verify a test asserts the token is reused across two consecutive calls.
- [x] 2.2 Implement `read_rows` against `GET /v4/spreadsheets/{id}/values/{worksheet}` with `UNFORMATTED_VALUE` and the required column range, and verify a fixture sheet with one data row returns the header and the row.

## 3. Sheets adapter and validation

- [x] 3.1 Add `SheetsPeriodRepository` implementing the port, mapping sheet columns onto the domain `Period` (no `source` column), and verify an adapter test round-trips a period to and from the sheet shape.
- [x] 3.2 Implement row validation (unparsable start, end-before-start, overlapping range, duplicate `period_id`) that excludes and reports invalid rows, and verify validation tests cover each exclusion case.
- [x] 3.3 Implement read-through caching in the coordinator (snapshot plus `last_sync`, `last_error`, `consecutive_failures`; unavailable after three failures) and verify a test asserts the cache is kept on failure and unavailable after the third consecutive failure.

## 4. Configuration and repair issues

- [x] 4.1 Add the `sheet` config step and options fields (spreadsheet id, worksheet name, service-account key path, poll interval) with pre-save validation against the header row, and verify a config-flow test rejects a missing column and accepts a valid sheet.
- [x] 4.2 Add `repairs.py` with the five failure-class issues created on failure and cleared on success, and verify a test asserts `sheet_auth_failed` is raised on a rejected token and cleared after a later success.
- [x] 4.3 Add the one-time import into an empty sheet and verify a test writes each cached period as a row and refuses when the sheet already has data.

## 5. Docs and integration check

- [x] 5.1 Update `README.md` with the Google Cloud / service-account setup, sharing steps, key rotation, and the privacy disclosure that Google can read the data, and verify the documented steps reference real config-flow fields.
- [x] 5.2 Run `openspec validate google-sheets-source-of-truth --strict` and `pre-commit run --all-files`, and verify both report no errors.
