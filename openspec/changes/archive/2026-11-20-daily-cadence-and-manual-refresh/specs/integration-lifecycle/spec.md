# Spec Delta

## MODIFIED Requirements

### Requirement: Release resources on unload

The system SHALL stop the coordinator and release its scheduled midnight timer
and any pending refresh callbacks when the config entry is unloaded, and SHALL
remove the coordinator from the integration's runtime data.

#### Scenario: Unload stops the update timer

- **WHEN** the config entry is unloaded
- **THEN** the coordinator is shut down, no midnight timer remains registered and no refresh remains scheduled

#### Scenario: Unload clears runtime data

- **WHEN** the config entry is unloaded
- **THEN** the integration's runtime data no longer holds a coordinator for that entry
