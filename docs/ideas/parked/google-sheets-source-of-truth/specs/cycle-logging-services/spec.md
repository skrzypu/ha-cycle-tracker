# Spec Delta

## Purpose

Keeps the logging-service contract accurate now that the configured Google Sheet,
not local storage, is the authoritative store.

## REMOVED Requirements

### Requirement: Persist cycle data locally

**Reason**: ADR-0004 makes the configured Google Sheet the source of truth.
Local storage is now only a cache.

## ADDED Requirements

### Requirement: Persist cycle data in the configured sheet

The system SHALL persist all recorded cycle data in the configured Google Sheet
and SHALL NOT treat local Home Assistant storage as authoritative. Local storage
SHALL be used only as a cache of the last successful read.

#### Scenario: Data survives reload

- **WHEN** period data is recorded and the integration is reloaded
- **THEN** the previously recorded data is restored by reading the sheet

#### Scenario: Sheet unavailable during a write

- **WHEN** a service is called while the sheet is not configured or unreachable
- **THEN** the service raises an error and no local write is made

#### Scenario: Cache is not a second source

- **WHEN** the cached snapshot differs from the sheet
- **THEN** the next successful read replaces the cache with the sheet contents

### Requirement: Service failure reporting

The `log_start` and `log_end` services SHALL fail with a user-visible error that
names the cause when the sheet is not configured, the credentials are rejected,
or Google is unreachable, and SHALL NOT report success unless the write reached
the sheet.

#### Scenario: Not configured

- **WHEN** `log_start` is called before the sheet configuration exists
- **THEN** the call fails with an error that points to the sheet configuration
  step

#### Scenario: Write rejected

- **WHEN** Google rejects the write request
- **THEN** the call fails with the returned reason and the cache is unchanged
