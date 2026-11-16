# Spec Delta

## ADDED Requirements

### Requirement: Release resources on unload

The system SHALL stop the coordinator's periodic refresh and release its
scheduled callbacks when the config entry is unloaded, and SHALL remove the
coordinator from the integration's runtime data.

#### Scenario: Unload stops the update timer

- **WHEN** the config entry is unloaded
- **THEN** the coordinator is shut down and no refresh remains scheduled

#### Scenario: Unload clears runtime data

- **WHEN** the config entry is unloaded
- **THEN** the integration's runtime data no longer holds a coordinator for that entry
