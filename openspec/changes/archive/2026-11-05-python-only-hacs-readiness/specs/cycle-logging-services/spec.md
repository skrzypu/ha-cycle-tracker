# Spec Delta

## Purpose

Provides Home Assistant services that let users record the start and end of a menstrual period, persists that data locally, and keeps the services registered correctly across the integration lifecycle.

## ADDED Requirements

### Requirement: Log period start service
The system SHALL expose a `log_start` service that records a period start date and an optional flow intensity, updating an existing record when the date matches the latest start.

#### Scenario: Valid start logged
- **WHEN** `log_start` is called with a date
- **THEN** a period record with that start date is stored and the service reports success

#### Scenario: Invalid flow intensity
- **WHEN** `log_start` is called with a flow intensity outside the allowed set
- **THEN** the call is rejected with a validation error

### Requirement: Log period end service
The system SHALL expose a `log_end` service that sets the end date of the latest open period, and SHALL reject the call when no open period exists or the period has already ended.

#### Scenario: End logged
- **WHEN** `log_end` is called while a period with no end date exists
- **THEN** that period's end date is stored and the service reports success

#### Scenario: No open period
- **WHEN** `log_end` is called and no period has been started
- **THEN** the service reports failure without changing stored data

### Requirement: Persist cycle data locally
The system SHALL persist all recorded cycle data using local Home Assistant storage and SHALL NOT transmit it to any external or cloud service.

#### Scenario: Data survives reload
- **WHEN** period data is recorded and the integration is reloaded
- **THEN** the previously recorded data is restored from local storage

### Requirement: Service lifecycle
The system SHALL register its services when the config entry is set up and SHALL unregister them when the config entry is unloaded, leaving no duplicate or orphaned service registrations.

#### Scenario: Services removed on unload
- **WHEN** the config entry is unloaded
- **THEN** `log_start` and `log_end` are no longer registered
