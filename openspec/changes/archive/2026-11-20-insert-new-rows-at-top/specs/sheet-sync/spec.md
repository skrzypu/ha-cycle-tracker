# Spec Delta: sheet-sync

## ADDED Requirements

### Requirement: Blank rows are ignored on read

Fully blank data rows SHALL be treated as absent when the sheet is read: they
SHALL NOT be reported as invalid rows and SHALL NOT count as data rows when
deciding whether the sheet already contains periods.

#### Scenario: Blank row is not reported invalid
- **WHEN** a data row below the header is fully blank
- **THEN** it is skipped without an invalid-row report and does not affect derived values or entities

#### Scenario: Blank-only sheet counts as empty
- **WHEN** the sheet has a header and only blank data rows
- **THEN** it is treated as having no data rows for purposes of the one-time import of cached periods

## MODIFIED Requirements

### Requirement: Write period start

The `log_start` service SHALL write a new period directly below the header
(row 2) with a generated `period_id`, the supplied start date, the optional flow
intensity, an empty end date, and a timestamp in `updated_at`. A blank row 2
SHALL be filled rather than adding another row, and an existing `period_id`
SHALL be updated in place. When the latest row has no end date and the same
start date, that row SHALL be updated instead of creating a duplicate.

#### Scenario: New period appended
- **WHEN** `log_start` is called for a `period_id` that is not yet in the sheet
- **THEN** one row is inserted directly below the header (row 2) and a refresh is requested

#### Scenario: Blank row 2 reused
- **WHEN** `log_start` is called for a new `period_id` and row 2 is blank
- **THEN** the values are written into row 2 without inserting an additional row

#### Scenario: Existing period updated in place
- **WHEN** `log_start` is called with a `period_id` already present in the sheet
- **THEN** that existing row is updated in place and no new row is inserted

#### Scenario: Same-day start updated
- **WHEN** `log_start` is called and the latest row is open with the same start date
- **THEN** the existing row is updated and no second row is created

#### Scenario: Ambiguous append failure
- **WHEN** a row insertion fails after the server may have accepted it, or the insertion succeeds but the subsequent value write fails
- **THEN** the integration re-reads the sheet and reuses the row with the same `period_id` or the blank row at row 2 instead of inserting a duplicate

### Requirement: Row validation

The integration SHALL validate every data row and SHALL exclude invalid rows
from predictions and statistics while continuing to use valid rows.

Invalid rows SHALL be reported in a repair issue that identifies the row
numbers.

#### Scenario: Invalid date
- **WHEN** a row has an unparsable or missing start date
- **THEN** the row is excluded and reported, and the remaining rows still render

#### Scenario: End before start
- **WHEN** a row has an end date earlier than its start date
- **THEN** the row is excluded and reported

#### Scenario: Overlapping periods
- **WHEN** two rows describe periods whose date ranges overlap
- **THEN** the later-starting row is excluded and reported, and predictions use the earlier valid row

#### Scenario: Duplicate period identifier
- **WHEN** two rows share a `period_id`
- **THEN** only the row with the newest `updated_at` is used and the duplicate is reported; when neither row has an `updated_at`, the row with the smaller row number (the higher row) is used

### Requirement: Writes request an immediate re-read

After a successful write through `log_start` or `log_end`, the integration
SHALL request an immediate re-read of the configured sheet rather than
publishing an in-memory snapshot only. The re-read SHALL update the last
successful read time.

#### Scenario: Start write triggers a re-read
- **WHEN** `log_start` successfully inserts, fills a blank row, or updates a row
- **THEN** the sheet is re-read immediately and the entities reflect the sheet contents

#### Scenario: End write triggers a re-read
- **WHEN** `log_end` successfully updates a row
- **THEN** the sheet is re-read immediately and the entities reflect the sheet contents

#### Scenario: Failed write does not trigger a re-read
- **WHEN** a write fails before reaching the sheet
- **THEN** no re-read is requested and the last successful read time is unchanged
