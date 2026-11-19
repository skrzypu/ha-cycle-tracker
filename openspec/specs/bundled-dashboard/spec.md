# bundled-dashboard Specification

## Purpose

Defines the bundled Lovelace dashboard the integration creates so the card has
a sidebar entry out of the box: when the dashboard is created, how it is seeded,
when it must not be touched, and how it is cleaned up.

## Requirements

### Requirement: Bundled dashboard creation

The integration SHALL create a single storage-mode Lovelace dashboard at a
stable hyphenated URL path with a sidebar entry, SHALL do so only when no
dashboard or panel already owns that URL path, SHALL NOT fail setup when the
dashboard cannot be created, and SHALL NOT modify any dashboard it did not
create.

#### Scenario: Dashboard created on setup

- **WHEN** the integration is set up, Lovelace runs in storage mode, and no
  dashboard owns the URL path
- **THEN** a dashboard titled "Cykl" is created with a sidebar entry and the
  card as its only view

#### Scenario: Existing dashboard left untouched

- **WHEN** a dashboard or panel already exists at the URL path and the
  integration did not create it
- **THEN** the integration does not create, overwrite, or seed it

#### Scenario: Setup survives a failure

- **WHEN** the dashboard cannot be created (Lovelace not ready, panel conflict,
  or an unexpected error)
- **THEN** integration setup still completes and the failure is logged

### Requirement: Initial view seeding

The integration SHALL seed the created dashboard with a single view containing
one `{"type": "custom:cycle-tracker-card"}` per Cycle Tracker device, bound by
`device_id` and never by an entity ID, ordered deterministically by device name
and then device id. A single-device installation SHALL get one card titled
`Cykl`; a multi-device installation SHALL title each card with its device name.
The integration SHALL seed only when the dashboard has no saved configuration
yet, SHALL never overwrite a user-edited dashboard, and SHALL NOT add a card for
an entry created later (the existing dashboard is left untouched).

#### Scenario: Seed on first creation

- **WHEN** the integration creates the dashboard on a single-person install
- **THEN** its saved configuration contains exactly one view with one cycle
  tracker card carrying the device's `device_id`

#### Scenario: Several people in one home

- **WHEN** two Cycle Tracker entries exist as two devices named `Anna` and `Beata`
- **THEN** the seeded view holds two cards, in that order, each with its own
  `device_id` and the device name as its title

#### Scenario: User edits preserved

- **WHEN** the dashboard the integration created has been edited by the user
- **THEN** the integration does not restore the original view

### Requirement: Ownership marker

The integration SHALL record that it created the dashboard and the view it
seeded, so that it never removes a user dashboard, never re-creates a dashboard
the user deleted, and only removes the dashboard while it still equals the
seeded view.

#### Scenario: User deletion respected

- **WHEN** the user deletes the dashboard the integration created
- **THEN** the integration does not create it again on a later restart

### Requirement: Dashboard removal with the last entry

When the last `cycle_tracker` config entry is removed, the integration SHALL
delete the bundled dashboard only when its saved configuration still matches the
original seeded view.

#### Scenario: Unmodified dashboard removed

- **WHEN** the last entry is removed and the dashboard still holds the seeded
  view
- **THEN** the dashboard and its sidebar entry are removed

#### Scenario: Edited dashboard kept

- **WHEN** the last entry is removed and the dashboard has been edited
- **THEN** the dashboard is left in place
