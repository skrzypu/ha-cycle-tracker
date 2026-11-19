# Spec Delta

## ADDED Requirements

### Requirement: Report a lifetime cycle-length average

The system SHALL report one additional lifetime average cycle length computed
from all in-range completed cycles in recorded history, in addition to the
windowed average. A cycle is in range when its length falls within the configured
outlier bounds (15 to 90 days by default): outlier cycles SHALL be excluded,
cycles recorded before the most recent long gap SHALL be included, and an open
period SHALL contribute no length. When no in-range cycle exists the lifetime
average SHALL be unknown.

#### Scenario: Outlier excluded from the lifetime average

- **WHEN** the recorded cycle lengths are 28, 10 and 30 days
- **THEN** the lifetime average is 29 days (28 and 30 only), the outlier warning remains, and the windowed average also excludes the 10-day cycle

#### Scenario: Cycles before a long gap are included

- **WHEN** cycles of 27 and 29 days were recorded before a 187-day gap and cycles of 30 and 31 days after it, with a configured window of 6
- **THEN** the windowed average uses only 30 and 31, while the lifetime average uses 27, 29, 30 and 31

#### Scenario: No in-range cycle

- **WHEN** recorded history contains only one open period or only out-of-range cycles
- **THEN** the lifetime average is unknown rather than a numeric zero

## MODIFIED Requirements

### Requirement: Report cycle statistics

The system SHALL report average cycle length, average period length, standard
deviations, total tracked cycles, and a prediction confidence value, and SHALL
degrade gracefully when fewer than two cycles exist. Cycle-length statistics
SHALL use the same usable N-cycle window as the prediction, where N is the
configured shared history window, and period-length statistics SHALL use
completed periods only.

#### Scenario: Single cycle tracked

- **WHEN** only one period is recorded
- **THEN** statistics report the configured lengths, zero deviations, and a tracked-cycle count of one

#### Scenario: Multiple cycles tracked

- **WHEN** multiple periods are recorded
- **THEN** average and standard-deviation values are computed from the recorded cycle lengths in the prediction window

#### Scenario: Window follows the configured setting

- **WHEN** the configured history window is 12 and twelve usable cycles exist
- **THEN** the windowed cycle-length average and standard deviation are computed from all twelve cycles

#### Scenario: Open period excluded from period statistics

- **WHEN** the latest period has no end date
- **THEN** period-length statistics use completed periods only and do not fail

#### Scenario: Confidence reported

- **WHEN** a prediction exists
- **THEN** the statistics report a confidence value between 0 and 1 plus its band
