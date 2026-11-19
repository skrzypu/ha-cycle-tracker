# Spec Delta

## MODIFIED Requirements

### Requirement: Exclude out-of-range cycles from prediction

The system SHALL exclude cycles shorter than the lower bound and longer than the
upper bound from prediction, using bounds supplied by configuration that default
to 15 and 90 days. Excluded cycles SHALL remain in recorded history and in the
tracked-period count with a warning, but SHALL be excluded from both cycle-length
averages.

#### Scenario: Long cycle excluded with a narrowed upper bound

- **WHEN** the upper bound is configured to 60 days and the recorded cycle lengths are 28, 29, 75 and 30 days
- **THEN** prediction uses 28, 29 and 30 and reports an outlier warning for the 75-day cycle

#### Scenario: Short cycle excluded from prediction

- **WHEN** the recorded cycle lengths are 28, 10 and 29 days
- **THEN** prediction uses 28 and 29 and reports a warning for the 10-day cycle

#### Scenario: Outlier excluded from both averages

- **WHEN** the recorded cycle lengths are 28, 10 and 30 days
- **THEN** neither the windowed nor the lifetime cycle-length average includes the 10-day cycle, and a warning names that period

### Requirement: Select the last six usable completed cycles

The system SHALL filter cycles before selecting the history window, and SHALL use
at most the N most recent cycles that remain after filtering, where N is the
shared configured history window (a whole number from 6 to 24). An excluded cycle
SHALL NOT occupy a slot in the window, and N SHALL apply to both prediction and
cycle-length statistics.

#### Scenario: Filtering happens before the window

- **WHEN** the configured window is 6 and the filtered cycle lengths are 27, 28, 29, 28, 30, 28, 31 and 29 days
- **THEN** prediction uses 29, 28, 30, 28, 31 and 29 (the six most recent) and ignores 27 and 28

#### Scenario: Window is shorter than six

- **WHEN** only three usable cycles remain after filtering
- **THEN** prediction uses all three

#### Scenario: Configured window larger than six

- **WHEN** the configured window is 12 and eight usable cycles remain after filtering
- **THEN** prediction and the windowed cycle-length average use all eight cycles

#### Scenario: Window is shorter than the configured N

- **WHEN** only three usable cycles remain after filtering and the configured window is 12
- **THEN** prediction uses all three

### Requirement: Report prediction confidence

The system SHALL report a confidence value between 0 and 1 computed as
`min(1, 1 - sigma / mean) * min(1, n / N)`, where sigma and mean come from the
usable cycle lengths, n is their count and N is the configured shared history
window, together with a band of low below 0.4, medium from 0.4 to 0.7, and high
above 0.7.

#### Scenario: Two cycles score low

- **WHEN** the usable lengths are 28 and 28 and the configured window is 6
- **THEN** confidence is about 0.33 and the band is low

#### Scenario: Four variable cycles score medium

- **WHEN** the usable lengths are 25, 32, 26 and 33 and the configured window is 6
- **THEN** confidence is about 0.59 and the band is medium

#### Scenario: Six stable cycles score high

- **WHEN** six usable cycles are recorded with a standard deviation of one day and a mean of 28 days, and the configured window is 6
- **THEN** confidence is about 0.96 and the band is high

#### Scenario: The denominator follows the configured window

- **WHEN** the same six stable cycles (sigma one day, mean 28 days) are evaluated first with a window of 6 and then with a window of 12
- **THEN** confidence falls from about 0.96 (high) to about 0.48 (medium), and no value is clamped to one merely because six cycles exist
