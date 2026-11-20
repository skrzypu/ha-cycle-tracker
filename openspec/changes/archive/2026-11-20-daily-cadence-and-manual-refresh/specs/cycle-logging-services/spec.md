# Spec Delta

## MODIFIED Requirements

### Requirement: Service lifecycle

The system SHALL register its services when the config entry is set up and SHALL unregister them when the config entry is unloaded, leaving no duplicate or orphaned service registrations. The registered services SHALL be `log_start`, `log_end` and `refresh`.

#### Scenario: Services removed on unload

- **WHEN** the config entry is unloaded
- **THEN** `log_start`, `log_end` and `refresh` are no longer registered

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

#### Scenario: Refresh targeted at the refresh button

- **WHEN** `refresh` is called with `target: {entity_id: button.cycle_tracker_refresh}`
- **THEN** the re-read is applied to the entry that owns that button

#### Scenario: Target of another integration

- **WHEN** `log_start` is called targeting an entity that belongs to a different integration
- **THEN** the call fails with a validation error and no period is recorded

#### Scenario: Ambiguous entry

- **WHEN** two config entries are configured and `log_start` is called without a target
- **THEN** the call fails with a validation error and no period is recorded
