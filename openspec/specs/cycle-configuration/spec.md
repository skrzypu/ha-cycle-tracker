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
history window, prediction algorithm, notification offset, notification toggle
and notification time — in a single form, and SHALL persist submitted values as
the entry's options.

#### Scenario: Options dialog opens

- **WHEN** the user opens the options dialog for a configured entry
- **THEN** a single form is shown pre-filled with the values currently in force, including the effective history window

#### Scenario: Saved settings take effect

- **WHEN** the dialog is submitted with a different cycle length
- **THEN** the entry options store that value and the integration reports the new cycle length after the entry reloads

#### Scenario: Saved window takes effect

- **WHEN** the dialog is submitted with a different history window
- **THEN** the entry options store that value and both the prediction and the windowed cycle-length average use it after the entry reloads
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

### Requirement: Configure the shared history window

The system SHALL expose one whole-number history-window setting in the range 6 to
24, editable during setup and in the options dialog, and SHALL NOT expose a
service to change it. One value SHALL feed both prediction and cycle-length
statistics. A config entry created through setup SHALL store 12 in its setup
data; an entry with neither an option nor a setup value for the window SHALL
resolve to the built-in default of 6, with no migration of existing entries.

#### Scenario: New entry stores twelve

- **WHEN** a config entry is created through the setup flow and the user leaves the history window untouched
- **THEN** the entry's setup data records a window of 12 and the integration uses 12 for prediction and cycle-length statistics

#### Scenario: Existing entry falls back to six

- **WHEN** an existing config entry has neither a saved option nor a setup value for the history window
- **THEN** the effective window is 6 without any migration or rewrite of the entry

#### Scenario: Options override the stored value

- **WHEN** the user saves a history window of 18 in the options dialog and the entry reloads
- **THEN** 18 is used for prediction and for the windowed cycle-length average

#### Scenario: Value outside the range is rejected

- **WHEN** a history window of 5 or 25 is submitted
- **THEN** the setting is not accepted
