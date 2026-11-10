# Spec Delta

## Purpose

Defines the Lovelace card that gives the integration a one-tap logging surface:
how the card is delivered and registered by the integration, how it is
configured, what it renders, which services its actions call, and how it behaves
when data or services are unavailable.

## ADDED Requirements

### Requirement: Card asset delivery

The integration SHALL serve the card as a static asset from a stable URL under
the Home Assistant HTTP server, and the URL SHALL include the integration
version as a query parameter so that a new release is not served from a stale
browser cache.

#### Scenario: Card asset reachable

- **WHEN** the integration is set up and Home Assistant is running
- **THEN** an HTTP GET of the card URL returns the JavaScript module with a
  JavaScript content type

#### Scenario: Version cache busting

- **WHEN** the manifest version changes in a new release
- **THEN** the registered Lovelace resource URL carries the new version as its
  query parameter

### Requirement: Lovelace resource registration

The integration SHALL register the card as a Lovelace resource when Lovelace
runs in storage mode, SHALL update the existing resource instead of creating a
duplicate when one already points at the card URL, and SHALL NOT fail setup when
the resource cannot be registered.

#### Scenario: Resource created on first start

- **WHEN** the integration starts and no Lovelace resource points at the card URL
- **THEN** exactly one resource pointing at the card URL is created

#### Scenario: Repeated start is idempotent

- **WHEN** the integration restarts while the resource already exists
- **THEN** the resource count for the card URL stays at one and its version
  query parameter is updated if needed

#### Scenario: YAML-mode Lovelace

- **WHEN** Lovelace runs in YAML mode and resources are not managed by Home Assistant
- **THEN** the integration completes setup without error and does not create a
  resource, and the documented manual resource entry applies

#### Scenario: Resource removed with the entry

- **WHEN** the config entry is deleted
- **THEN** the Lovelace resource created by the integration is removed

### Requirement: Card configuration

The card SHALL accept `type: custom:cycle-tracker-card` with an optional
`title`, an optional `entities` mapping, and an optional `show_actions` flag.

`entities` SHALL support the keys `cycle_day`, `cycle_phase`, `next_period`,
`days_until_period`, and `days_until_ovulation`, each defaulting to the
integration's conventional entity ID when omitted. `show_actions` SHALL default
to `true`.

#### Scenario: Minimal configuration

- **WHEN** the card is added with only its type
- **THEN** it uses the title "Cycle Tracker", the conventional entity IDs, and
  shows the action buttons

#### Scenario: Entity override

- **WHEN** the configuration provides a custom entity ID for `cycle_day`
- **THEN** the card reads that entity instead of the conventional one

#### Scenario: Actions hidden

- **WHEN** the configuration sets `show_actions: false`
- **THEN** the card renders values only and no logging buttons

### Requirement: Card content

The card SHALL display the current cycle day, current cycle phase, next period
date, days until the next period, and days until the next ovulation, using the
Home Assistant state machine as the only data source.

When an entity is missing, unavailable, or unknown, the card SHALL render an
explicit "not tracked" state for that value and SHALL continue to render the
remaining values.

#### Scenario: Values rendered

- **WHEN** all configured entities have valid states
- **THEN** each value is shown with its label and unit or formatted date

#### Scenario: Missing entity

- **WHEN** one configured entity does not exist in the state machine
- **THEN** that row shows a not-tracked state and the other rows still render

#### Scenario: No cycle data yet

- **WHEN** the integration has no recorded period and the sensors report unknown
- **THEN** the card shows the not-tracked state instead of a numeric zero or an
  empty value

### Requirement: Logging actions

The card SHALL provide a start action that calls `cycle_tracker.log_start` and
an end action that calls `cycle_tracker.log_end`, both with the user's local
date in `YYYY-MM-DD` format.

The end action SHALL require an inline confirmation before calling the service.
Both actions SHALL be disabled while a service call is in flight, and a service
error SHALL be surfaced in the card without discarding the rendered values.

#### Scenario: Start logged

- **WHEN** the user activates the start action
- **THEN** the card calls `cycle_tracker.log_start` once with today's local date
  and reports success

#### Scenario: End requires confirmation

- **WHEN** the user activates the end action
- **THEN** the card first asks for confirmation and calls
  `cycle_tracker.log_end` only after the user confirms

#### Scenario: Service rejects the call

- **WHEN** `cycle_tracker.log_end` is rejected because no period is open
- **THEN** the card shows the returned error message and keeps the current values
  visible

#### Scenario: Repeated activation

- **WHEN** a service call is already in flight
- **THEN** both action buttons are disabled until the call settles

### Requirement: Card picker metadata

The card SHALL register itself in `window.customCards` with its element type, a
human-readable name, and a description, so that it can be found in the Lovelace
card picker.

#### Scenario: Card listed in the picker

- **WHEN** the card module is loaded in the frontend
- **THEN** the picker lists "Cycle Tracker Card" with a description and without
  a live preview

### Requirement: Accessibility and theming

The card SHALL use native interactive elements that are keyboard operable and
expose accessible names, SHALL announce action results through a polite live
region, and SHALL style itself only with Home Assistant theme variables so that
it follows light and dark themes.

#### Scenario: Keyboard operation

- **WHEN** the user navigates the card with the keyboard
- **THEN** each action is reachable and activatable without a pointer

#### Scenario: Action result announced

- **WHEN** a logging action succeeds or fails
- **THEN** the result is announced through a polite live region

#### Scenario: Theme change

- **WHEN** the active Home Assistant theme changes between light and dark
- **THEN** the card keeps readable contrast without a reload
