# integration-lifecycle Specification

## Purpose
The integration's lifecycle in Home Assistant: what is created when a config
entry is set up, what is released when it unloads, and how an options change
reaches the running entities. Unloading stops the coordinator and clears the
entry's runtime data; a reload goes through the config entry manager so the
entry is in the state Home Assistant's first refresh expects.

## Requirements

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
