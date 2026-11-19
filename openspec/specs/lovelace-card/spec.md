# lovelace-card Specification

## Purpose

Defines the Lovelace card that gives the integration a one-tap logging surface
in Polish: how the card is delivered and registered by the integration, how it
is configured, what the stat card renders, which services its actions call and
when the actions are disabled, and how it behaves when data or services are
unavailable.

## Requirements

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

#### Scenario: Resource removed with the last entry

- **WHEN** the config entry is deleted and no other `cycle_tracker` entry remains
- **THEN** the Lovelace resource created by the integration is removed

### Requirement: Card configuration

The card SHALL accept `type: custom:cycle-tracker-card` with an optional
`title`, an optional `entities` mapping, and an optional `show_actions` flag
that defaults to `true`.

`entities` SHALL support the keys `cycle_day`, `cycle_start`, `cycle_phase`,
`next_period`, `next_ovulation`, `days_until_period`, `days_until_ovulation`,
`statistics`, and `period_open`, each defaulting to the integration's
conventional entity ID when omitted.

The card additionally accepts an optional `device_id` that binds it to a
specific Cycle Tracker device (device registry id, one per config entry /
person). Entities are then resolved from that device's entity registry entries,
first by the conventional name suffix (for example
`*_cycle_tracker_cycle_day`) and otherwise by the stable `unique_id` suffix
(`<entry_id>_cycle_day`), so a renamed entity is still found; an explicit
`entities` override wins for the keys it covers. A card editor
(`getConfigElement` / `getStubConfig`) lets the user pick the device by name
— showing the area name next to it when one is set — instead of typing entity
IDs. With no `device_id` and exactly one Cycle Tracker device the card binds to
it automatically; with several devices and none selected it renders a Polish
message asking the user to pick the device in the editor and never guesses.

#### Scenario: Bound entity was renamed

- **WHEN** the card is bound to a device and one of its entities has an
  arbitrary `entity_id` that does not carry the conventional suffix
- **THEN** the card finds that entity through the matching `unique_id` suffix

#### Scenario: Minimal configuration

- **WHEN** the card is added with only its type
- **THEN** it uses the title "Cycle Tracker", the conventional entity IDs, and
  shows the action buttons

#### Scenario: Entity override

- **WHEN** the configuration provides a custom entity ID for `cycle_day`
- **THEN** the card reads that entity instead of the conventional one

#### Scenario: Entity ID gained a prefix

- **WHEN** the conventional entity ID does not exist because Home Assistant
  prefixed it with an area or device name and an entity in the same domain ends
  with the conventional name
- **THEN** the card reads that entity, and an explicit `entities` override still
  takes precedence

#### Scenario: Two devices on one dashboard

- **WHEN** two Cycle Tracker config entries exist (one per person, each with its
  own device) and two cards are placed on one dashboard view
- **THEN** each card is bound to a different device through the card editor,
  each card renders its device name as a small caption next to its title, and
  the three headline values come from the matching device only
- **AND** a card with no device selected shows a Polish message asking to pick
  the device instead of guessing data

#### Scenario: Actions hidden

- **WHEN** the configuration sets `show_actions: false`
- **THEN** the card renders values only and no logging buttons

### Requirement: Stat card content

The card SHALL render the current cycle day (with its start date), the
days-until-period count, and the prediction confidence as equally dominant
headline values, the current cycle phase with its Polish name and a one-line
plain-language Polish description, and the next period and next ovulation
dates, using Home Assistant entity states as the only data source.

#### Scenario: Values rendered

- **WHEN** all configured entities have valid states
- **THEN** the cycle day, days-until-period, and confidence values are visually
  dominant, and the phase, the cycle start date, both dates, and their labels
  are shown

#### Scenario: Cycle start date shown

- **WHEN** the cycle start sensor reports a date
- **THEN** the card shows that date as a caption under the cycle day headline

#### Scenario: Confidence shown with its band

- **WHEN** the statistics sensor reports a prediction confidence
- **THEN** the card shows the confidence as a whole percentage with its Polish
  band name (niska / średnia / wysoka) as a dominant headline

#### Scenario: Phase description follows the phase

- **WHEN** the phase sensor reports a known phase
- **THEN** the card shows that phase's Polish name and its fixed plain-language
  description

#### Scenario: Polish labels

- **WHEN** the card renders
- **THEN** every label, action label, and status message is in Polish

### Requirement: Degraded states

When an entity is missing, unavailable, or unknown, the card SHALL render an
explicit not-tracked state for that value and SHALL continue to render the
remaining values.

#### Scenario: Missing entity

- **WHEN** one configured entity does not exist in the state machine
- **THEN** that row shows a not-tracked state and the other rows still render

#### Scenario: No cycle data yet

- **WHEN** the integration has no recorded period and the sensors report unknown
- **THEN** the card shows the not-tracked state instead of a numeric zero or an
  empty value

### Requirement: Collapsible statistics

The card SHALL show cycle statistics inside a collapsible disclosure that starts
closed and SHALL NOT present statistics in tabs. The disclosure SHALL show the
windowed and the lifetime average cycle length as two separately labelled rows,
alongside the average period length and the tracked cycle count, using the
statistics sensor's attributes only. No separate card or chart is required for
these averages.

#### Scenario: Statistics collapsed by default

- **WHEN** the card renders with the statistics entity available
- **THEN** the statistics values are hidden behind a closed disclosure labeled in Polish

#### Scenario: Statistics expanded

- **WHEN** the user activates the disclosure
- **THEN** the statistics values (windowed average cycle length, lifetime average cycle length, average period length, and tracked cycle count) are shown

#### Scenario: Both averages are labelled rows

- **WHEN** the statistics sensor reports both a windowed and a lifetime average cycle length
- **THEN** the card shows two distinct rows with Polish labels that identify which average each value is

#### Scenario: Lifetime average unavailable

- **WHEN** the statistics sensor has no lifetime average value
- **THEN** that row shows the not-tracked state and the windowed average row still renders

#### Scenario: Statistics missing

- **WHEN** the statistics entity is missing or unknown
- **THEN** the disclosure shows a not-tracked state instead of empty values
### Requirement: Logging actions

The card SHALL provide a start action that calls `cycle_tracker.log_start` and
an end action that calls `cycle_tracker.log_end`, both with the user's local
date in `YYYY-MM-DD` format, and SHALL interact with recorded cycle data only
through these two services, never by reading or writing storage directly.

#### Scenario: Start logged

- **WHEN** the user activates the start action
- **THEN** the card calls `cycle_tracker.log_start` once with today's local date
  and reports success

#### Scenario: Local date near midnight

- **WHEN** the user activates an action in a non-UTC time zone
- **THEN** the sent date is the browser's local calendar day, not the UTC day

### Requirement: Action safety

The card SHALL disable the start action while the period-open entity is on and
disable the end action while it is off, SHALL require an inline confirmation
before calling `log_end`, SHALL disable both actions while a service call is in
flight, and SHALL surface a service error in the card without discarding the
rendered values.

#### Scenario: Start disabled while a period is open

- **WHEN** the period-open entity reports on
- **THEN** the start action is disabled and activating it calls no service

#### Scenario: End disabled while no period is open

- **WHEN** the period-open entity reports off
- **THEN** the end action is disabled and activating it calls no service

#### Scenario: End requires confirmation

- **WHEN** the user activates the end action while a period is open
- **THEN** the card first asks for confirmation and calls
  `cycle_tracker.log_end` only after the user confirms

#### Scenario: Service rejects the call

- **WHEN** a logging service rejects the call
- **THEN** the card shows the returned error message and keeps the current
  values visible

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
- **THEN** each action and the statistics disclosure are reachable and
  activatable without a pointer

#### Scenario: Action result announced

- **WHEN** a logging action succeeds or fails
- **THEN** the result is announced through a polite live region

#### Scenario: Theme change

- **WHEN** the active Home Assistant theme changes between light and dark
- **THEN** the card keeps readable contrast without a reload
