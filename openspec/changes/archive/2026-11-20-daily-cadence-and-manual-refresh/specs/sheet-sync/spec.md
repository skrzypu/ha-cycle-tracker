# Spec Delta

## MODIFIED Requirements

### Requirement: Sync freshness and availability

The integration SHALL read the sheet once per local calendar day at midnight
and whenever a refresh is requested, SHALL expose the time of the last
successful read as an entity attribute, and SHALL mark the entities unavailable
after three consecutive failed reads. Availability semantics are not changed by
this requirement.

#### Scenario: Daily midnight read

- **WHEN** local midnight arrives while the integration is running
- **THEN** the sheet is read and the derived values reflect the new calendar day

#### Scenario: Fresh data

- **WHEN** the last successful read was within the current calendar day
- **THEN** the entities report as available with a current `last_sync` attribute value

#### Scenario: Stale data

- **WHEN** three consecutive reads fail
- **THEN** the entities report as unavailable and retain the last known values

#### Scenario: Refresh after write

- **WHEN** a service successfully writes to the sheet
- **THEN** a refresh is requested immediately instead of waiting for midnight

## ADDED Requirements

### Requirement: Refresh on demand

The integration SHALL expose a `cycle_tracker.refresh` service and a button
entity that request an immediate re-read of the configured sheet. A successful
refresh SHALL update the last successful read time and republish entity state.
A failed refresh SHALL keep the last successful snapshot.

#### Scenario: Service refresh

- **WHEN** `cycle_tracker.refresh` is called for a configured entry
- **THEN** the sheet is re-read immediately and the entities reflect the current sheet contents

#### Scenario: Button refresh

- **WHEN** the refresh button is pressed
- **THEN** the same refresh behavior as the service is performed for the button's entry

#### Scenario: Refresh failure keeps the snapshot

- **WHEN** a refresh cannot read the sheet
- **THEN** the last successful snapshot remains in use and the failure is recorded in the sync status

#### Scenario: No sheet configured

- **WHEN** a refresh is requested for an entry without sheet configuration
- **THEN** no read is performed and the entities remain unavailable

### Requirement: Writes request an immediate re-read

After a successful write through `log_start` or `log_end`, the integration
SHALL request an immediate re-read of the configured sheet rather than
publishing an in-memory snapshot only. The re-read SHALL update the last
successful read time.

#### Scenario: Start write triggers a re-read

- **WHEN** `log_start` successfully appends or updates a row
- **THEN** the sheet is re-read immediately and the entities reflect the sheet contents

#### Scenario: End write triggers a re-read

- **WHEN** `log_end` successfully updates a row
- **THEN** the sheet is re-read immediately and the entities reflect the sheet contents

#### Scenario: Failed write does not trigger a re-read

- **WHEN** a write fails before reaching the sheet
- **THEN** no re-read is requested and the last successful read time is unchanged
