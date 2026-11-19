# Spec Delta

## MODIFIED Requirements

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
