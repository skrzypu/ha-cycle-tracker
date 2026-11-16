# cycle-configuration Specification

## Purpose
Settings that the user can change after setup — cycle length, period length,
prediction algorithm, notification offset, notification toggle and notification
time — and the single place those values are read from. The config entry's
options take precedence over its setup data, which takes precedence over the
built-in defaults, so an edited setting is never shadowed by a stale copy in
stored data.

## Requirements

### Requirement: Change settings after setup

The system SHALL provide an options dialog for a configured entry that shows the
effective values of the configurable settings — cycle length, period length,
prediction algorithm, notification offset, notification toggle and notification
time — in a single form, and SHALL persist submitted values as the entry's
options.

#### Scenario: Options dialog opens

- **WHEN** the user opens the options dialog for a configured entry
- **THEN** a single form is shown pre-filled with the values currently in force

#### Scenario: Saved settings take effect

- **WHEN** the dialog is submitted with a different cycle length
- **THEN** the entry options store that value and the integration reports the new cycle length after the entry reloads

### Requirement: Resolve settings from the config entry

The system SHALL resolve every configurable setting from the entry's options,
falling back to the entry's setup data and then to the built-in default, and
SHALL keep recorded periods as the only content it persists in integration
storage. A setting copied into previously stored data SHALL NOT override the
config entry.

#### Scenario: Option overrides setup data

- **WHEN** an option is saved that differs from the setup value
- **THEN** the integration uses the option

#### Scenario: Setup data used without an option

- **WHEN** no option is saved for a setting
- **THEN** the integration uses the value recorded at setup

#### Scenario: Default used when nothing is configured

- **WHEN** neither the options nor the setup data contain a setting
- **THEN** the integration uses the built-in default for it

#### Scenario: Stored copy never wins

- **WHEN** integration storage still contains a setting value that differs from the config entry
- **THEN** the config entry's value is used
