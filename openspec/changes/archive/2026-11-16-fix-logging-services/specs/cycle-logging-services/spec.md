# Spec Delta

## ADDED Requirements

### Requirement: Resolve the target config entry

The system SHALL resolve the config entry a service call belongs to from the
call's target — an entity, device or area of this integration — and SHALL use
the only configured entry when the call carries no target. The system SHALL
reject a call whose target contains no entity of this integration, or whose
target spans several config entries, with a validation error, and SHALL leave
stored data unchanged in both cases.

#### Scenario: Call without a target on a single entry

- **WHEN** one config entry is configured and `log_start` is called with only a date
- **THEN** the call is applied to that entry's data

#### Scenario: Call targeted at an integration entity

- **WHEN** `log_start` is called with `target: {entity_id: sensor.cycle_tracker_cycle_day}`
- **THEN** the call is applied to the entry that owns that entity

#### Scenario: Target of another integration

- **WHEN** `log_start` is called targeting an entity that belongs to a different integration
- **THEN** the call fails with a validation error and no period is recorded

#### Scenario: Ambiguous entry

- **WHEN** two config entries are configured and `log_start` is called without a target
- **THEN** the call fails with a validation error and no period is recorded

## MODIFIED Requirements

### Requirement: Log period start service

The system SHALL expose a `log_start` service that records a period start date
and an optional flow intensity, updating an existing record when the date
matches the latest start. A newly recorded start SHALL remain an open period
until `log_end` records its end, and an open period SHALL NOT contribute a
length to period-length statistics.

#### Scenario: Valid start logged

- **WHEN** `log_start` is called with a date
- **THEN** a period record with that start date is stored and the service reports success

#### Scenario: Invalid flow intensity

- **WHEN** `log_start` is called with a flow intensity outside the allowed set
- **THEN** the call is rejected with a validation error

#### Scenario: Started period stays open

- **WHEN** `log_start` records a date and `log_end` has not been called
- **THEN** the period is reported as open and period-length statistics ignore it

### Requirement: Log period end service

The system SHALL expose a `log_end` service that sets the end date of the latest
open period, and SHALL reject the call when no open period exists, the period has
already ended, or the requested end date precedes the period start.

#### Scenario: End logged

- **WHEN** `log_end` is called while a period with no end date exists
- **THEN** that period's end date is stored and the service reports success

#### Scenario: No open period

- **WHEN** `log_end` is called and no period has been started
- **THEN** the service reports failure without changing stored data

#### Scenario: End before the period start

- **WHEN** `log_end` is called with a date earlier than the latest period start
- **THEN** the service reports failure and stored data is unchanged
