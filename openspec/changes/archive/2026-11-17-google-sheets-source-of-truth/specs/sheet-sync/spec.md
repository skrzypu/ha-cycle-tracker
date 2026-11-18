# Spec Delta

## Purpose

Defines how the integration connects to a user-owned Google Sheet, what the
sheet must contain, how periods are read and written, and what the user sees
when the sheet is missing, misconfigured, or unreachable.

## ADDED Requirements

### Requirement: Sheet configuration

The integration SHALL require a spreadsheet identifier, a worksheet name, and a
service account key file path before it reads or writes any data, and SHALL
store only the key file path in the config entry, never the key contents.

The key file path SHALL resolve inside the Home Assistant configuration
directory.

#### Scenario: Configuration accepted

- **WHEN** the user supplies a spreadsheet identifier, a worksheet name, and a readable service account key file
- **THEN** the integration validates the connection and the header row before creating the config entry

#### Scenario: Key file outside the configuration directory

- **WHEN** the supplied key file path resolves outside the Home Assistant configuration directory
- **THEN** the configuration step is rejected with a validation error and no entry is created

#### Scenario: Missing configuration

- **WHEN** a config entry has no sheet configuration
- **THEN** a repair issue explains how to configure the sheet and the entities report themselves as unavailable

### Requirement: Sheet schema

The worksheet SHALL have a header row in its first row containing the columns
`period_id`, `start_date`, `end_date`, `flow_intensity`, `notes`, and
`updated_at`.

Columns SHALL be mapped by header name, not by position. Extra columns SHALL be
ignored. Missing required columns SHALL be reported as a schema error.

#### Scenario: Valid header

- **WHEN** the first row contains all required column names in any order
- **THEN** the integration maps values by name and starts syncing

#### Scenario: Missing column

- **WHEN** a required column is absent from the header row
- **THEN** a schema repair issue lists the missing columns and no data is read

#### Scenario: Extra column

- **WHEN** the header row contains an additional column
- **THEN** the integration ignores it and syncs the required columns

### Requirement: Read periods from the sheet

The integration SHALL read period rows from the configured worksheet on each
coordinator refresh, SHALL treat the sheet as authoritative over any cached
copy, and SHALL keep the last successful snapshot when a read fails.

#### Scenario: Manual edit picked up

- **WHEN** a user edits a period's dates or flow intensity in the Sheet
- **THEN** the next successful refresh reflects the edited values in the entities

#### Scenario: Row deleted in the sheet

- **WHEN** a user deletes a period row in the Sheet
- **THEN** the period disappears from the entities after the next successful refresh

#### Scenario: Read failure keeps the snapshot

- **WHEN** a refresh fails because Google is unreachable
- **THEN** the entities keep the last successful values and the failure is recorded in the sync status

### Requirement: Write period start

The `log_start` service SHALL append a row with a generated `period_id`, the
supplied start date, the optional flow intensity, an empty end date, and a
timestamp in `updated_at`.

When the latest row has no end date and the same start date, the service SHALL
update that row instead of appending a duplicate.

#### Scenario: New period appended

- **WHEN** `log_start` is called and no open period starts on that date
- **THEN** one row is appended and a refresh is requested

#### Scenario: Same-day start updated

- **WHEN** `log_start` is called and the latest row is open with the same start date
- **THEN** the existing row is updated and no second row is appended

#### Scenario: Ambiguous append failure

- **WHEN** an append request fails after the server may have accepted it
- **THEN** the integration re-reads the sheet and reuses the existing row with the same `period_id` instead of appending a duplicate

### Requirement: Write period end

The `log_end` service SHALL set the end date and `updated_at` of the latest row
whose end date is empty, and SHALL reject the call when no such row exists.

#### Scenario: End written

- **WHEN** `log_end` is called while a row has an empty end date
- **THEN** that row's end date and timestamp are updated and a refresh is requested

#### Scenario: No open period

- **WHEN** `log_end` is called and every row already has an end date
- **THEN** the service reports failure and the sheet is unchanged

### Requirement: Row validation

The integration SHALL validate every row and SHALL exclude invalid rows from
predictions and statistics while continuing to use valid rows.

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
- **THEN** only the row with the newest `updated_at` is used and the duplicate is reported

### Requirement: Sync freshness and availability

The integration SHALL refresh on a configurable interval with a default of five
minutes, SHALL expose the time of the last successful sync, and SHALL mark the
entities unavailable when the last successful sync is older than three
intervals.

#### Scenario: Fresh data

- **WHEN** the last successful sync is within the configured interval
- **THEN** the entities report as available with a current `last_sync` value

#### Scenario: Stale data

- **WHEN** no sync has succeeded for three intervals
- **THEN** the entities report as unavailable and retain the last known values

#### Scenario: Refresh after write

- **WHEN** a service successfully writes to the sheet
- **THEN** a refresh is requested immediately instead of waiting for the next interval

### Requirement: Setup and failure guidance

The integration SHALL create a repair issue for each distinct failure class:
missing configuration, authentication failure, unreachable sheet, invalid
schema, and invalid rows. Each issue SHALL include the action needed to fix it.

#### Scenario: Authentication failure

- **WHEN** Google rejects the service account credentials
- **THEN** a repair issue names the credential problem and links to the reconfiguration step

#### Scenario: Unreachable sheet

- **WHEN** the spreadsheet identifier or worksheet name cannot be resolved
- **THEN** a repair issue names the sheet and the worksheet and explains how to correct them

#### Scenario: Issue clears after a fix

- **WHEN** a subsequent refresh succeeds
- **THEN** the corresponding repair issues are removed

### Requirement: One-time import of local periods

When the configured sheet has no data rows and the integration holds cached
periods, the configuration step SHALL offer a one-time import of those periods.

#### Scenario: Import accepted

- **WHEN** the user accepts the import during configuration
- **THEN** each cached period is written as a row with a generated `period_id`

#### Scenario: Import declined

- **WHEN** the user declines the import
- **THEN** the sheet stays empty and the cached periods are not written

#### Scenario: Sheet already has data

- **WHEN** the sheet already contains period rows
- **THEN** the import is not offered and the sheet is treated as authoritative
