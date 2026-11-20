# Spec Delta

## Purpose

Provides an optional, uncertainty-aware fertility estimate that shows the
existing estimated fertile window with its margin made explicit, in a dedicated
entity and on the card, without making any contraceptive promise.

## ADDED Requirements

### Requirement: Derive a fertility margin from population sigma

The system SHALL compute a margin of `max(2, ceil(sigma))` days from the same
population standard deviation of usable cycle lengths that already feeds the
period uncertainty window and confidence. The six-day base fertile window SHALL
remain unchanged; the margin only widens how that estimate is presented.

#### Scenario: Stable history uses the two-day floor

- **WHEN** the usable cycle lengths are 28 and 28, so sigma is 0
- **THEN** the margin is 2 days

#### Scenario: Variable history widens the margin

- **WHEN** the usable cycle lengths are 25, 32, 26 and 33, so sigma is about 3.5
- **THEN** the margin is 4 days

### Requirement: Report an extended fertility band

The system SHALL report an extended band around the ovulation center of a cycle
as `[ovulation_center - 5 - margin, ovulation_center + margin]`, where the base
window from the ovulation center minus five days through the center is
preserved. A larger margin from irregular cycles SHALL make the band wider.

#### Scenario: Band around a 28-day stable cycle

- **WHEN** the ovulation center is 2026-11-15 and the margin is 2 days
- **THEN** the base fertile window is 2026-11-10 to 2026-11-15 and the extended band is 2026-11-08 to 2026-11-17

#### Scenario: Band grows with irregular cycles

- **WHEN** the same ovulation center is 2026-11-15 but the margin is 4 days
- **THEN** the extended band is 2026-11-06 to 2026-11-19 and the days outside it are fewer

### Requirement: Classify the reference date against the estimated window

The system SHALL report `within_estimated_fertile_window` when the reference
date falls inside the extended band of the running cycle or of the next cycle,
and SHALL otherwise report `outside_estimated_fertile_window`. These are stable
technical state identifiers, not user-facing copy.

#### Scenario: Date inside the extended band

- **WHEN** the reference date is 2026-11-09, the current cycle's extended band is 2026-11-08 to 2026-11-17
- **THEN** the state is `within_estimated_fertile_window`

#### Scenario: Date outside the extended band

- **WHEN** the reference date is 2026-11-20, after the current band and before the next band
- **THEN** the state is `outside_estimated_fertile_window`

### Requirement: Require two usable cycles for an estimate

The system SHALL report `unknown` and SHALL NOT produce a fertile window or a
margin band when fewer than two usable completed cycles remain after filtering.
It SHALL NOT default to `outside_estimated_fertile_window` or substitute the
configured cycle length.

#### Scenario: One usable cycle

- **WHEN** only one usable completed cycle exists
- **THEN** the fertility estimate state is `unknown` and no window or band is reported

#### Scenario: No fallback to configured length

- **WHEN** no usable completed cycle exists and the configured cycle length is 28
- **THEN** the state remains `unknown`

### Requirement: Expose a dedicated fertility estimate entity

The system SHALL expose the estimate as a separate `fertility_estimate` entity,
not as an attribute of an existing sensor. Its technical state SHALL be one of
`outside_estimated_fertile_window`, `within_estimated_fertile_window` and
`unknown`, surfaced through a `translation_key` so that copy lives in
translations. It SHALL expose as attributes the estimated fertile window, the
margin band, `margin_days`, `confidence`, `confidence_band` and
`usable_cycle_count`, drawing confidence and its band from the existing
statistics.

#### Scenario: Entity is separate

- **WHEN** the feature is enabled and a prediction exists
- **THEN** a `fertility_estimate` entity appears and no existing sensor gains a fertility attribute

#### Scenario: Attributes reflect the model

- **WHEN** the estimate has margin 2 days, confidence 0.33 with band `low` and two usable cycles
- **THEN** the entity exposes the base window, the band, `margin_days` 2, `confidence` 0.33, `confidence_band` `low` and `usable_cycle_count` 2

### Requirement: Create the entity only when opted in

The system SHALL disable the `enable_fertility_estimate` option by default and
SHALL resolve it through the options → data → default resolver so that existing
entries without the key stay disabled without a migration. The toggle SHALL be
offered only in the options flow, never in initial setup. When disabled the
entity SHALL NOT be created at all, and changing the option SHALL reload the
config entry.

#### Scenario: Existing entry stays disabled

- **WHEN** a config entry predates the option and has no `enable_fertility_estimate` key
- **THEN** the resolver returns false and no `fertility_estimate` entity is created

#### Scenario: Enabling reloads the entry

- **WHEN** the user turns the option on in the options flow
- **THEN** the config entry is reloaded and the entity is created

#### Scenario: Not offered during initial setup

- **WHEN** the user walks through initial setup
- **THEN** no fertility-estimate toggle is shown

### Requirement: Present factual, non-contraceptive copy

The system SHALL present the state with the factual labels „poza szacowanym oknem
płodnym", „w szacowanym oknie płodnym" and „brak danych", with the uncertainty
in the same frame as the fact. It SHALL display the exact symmetric disclaimer
from BDR-0004 and SHALL NOT use the words „bezpieczny", „dni bezpieczne",
„możesz" or „ryzyko zajścia" in any copy for this feature.

#### Scenario: Factual label with the disclaimer

- **WHEN** the state is `within_estimated_fertile_window` and the card renders the section
- **THEN** it shows „w szacowanym oknie płodnym", the margin band beside it, and the full symmetric disclaimer

#### Scenario: Unknown label

- **WHEN** the state is `unknown`
- **THEN** it shows „brak danych" and no window or band is implied

### Requirement: Show the card section only when the entity exists

The system SHALL render the fertility section of the shipped card only when the
`fertility_estimate` entity is available, and SHALL omit the section otherwise
so no empty block appears.

#### Scenario: Section hidden when disabled

- **WHEN** the feature is disabled and the entity does not exist
- **THEN** the card shows no fertility section

#### Scenario: Section visible when enabled

- **WHEN** the entity exists
- **THEN** the card shows the fertility section, whose body carries the state and the disclaimer

#### Scenario: Fertility section follows statistics

- **WHEN** the card renders both the statistics section and the fertility section
- **THEN** the fertility section appears after the statistics section in the card document

### Requirement: Collapsible fertility section

The system SHALL present the fertility section of the shipped card as a
collapsible region that is collapsed by default. The section heading SHALL be a
button that toggles the region, carrying `aria-expanded` with the current state
and `aria-controls` pointing at the region, and SHALL respond to pointer
activation and to the Enter and Space keys. Collapsing SHALL hide the section
body — the state fact, the margin band and the disclaimer — while keeping it in
the product, and the card SHALL NOT persist the expanded state.

#### Scenario: Collapsed by default

- **WHEN** the card renders and the `fertility_estimate` entity exists
- **THEN** the section is present with its body hidden and the header reports `aria-expanded="false"`

#### Scenario: Header toggles the body

- **WHEN** the user activates the header with a click, Enter or Space
- **THEN** the body is shown and `aria-expanded` becomes `"true"`, and activating the header again hides the body and sets `aria-expanded` to `"false"`

#### Scenario: No entity means no collapsible region

- **WHEN** the `fertility_estimate` entity does not exist
- **THEN** the card renders neither the header nor the collapsible region

#### Scenario: Body content survives collapsing

- **WHEN** the section is collapsed
- **THEN** the state fact, the margin band and the disclaimer remain the section's content and are only hidden, so expanding shows the same copy and the disclaimer is never dropped

#### Scenario: Unknown state has no band when expanded

- **WHEN** the state is `unknown` and the user expands the section
- **THEN** it shows „brak danych" and no margin band is rendered

#### Scenario: Expanded state is not persisted

- **WHEN** the card is reloaded after the section was expanded
- **THEN** the section is collapsed again and no stored flag is read or written

### Requirement: Compute the fertility estimate deterministically

The system SHALL compute the estimate as a pure function of the recorded
periods, the configuration and a reference date supplied by the caller, and
SHALL NOT read the current date or persist derived values.

#### Scenario: Same inputs produce the same estimate

- **WHEN** the same periods, configuration and reference date are supplied twice
- **THEN** both estimates are identical

#### Scenario: Reference date is respected

- **WHEN** the same history is evaluated with two different reference dates
- **THEN** the state can differ while the margin band for the same ovulation center stays the same
