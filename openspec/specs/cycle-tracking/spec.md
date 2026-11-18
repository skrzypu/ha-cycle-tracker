# cycle-tracking Specification

## Purpose

Tracks recorded menstrual cycles and derives current cycle state, upcoming period and ovulation predictions, and cycle statistics that the integration exposes to Home Assistant.

## Requirements

### Requirement: Record menstrual periods

The system SHALL treat the configured Google Sheet as the source of recorded
periods, SHALL persist each period with an inclusive start date and an optional
end date, and SHALL keep records ordered by start date.

Each period SHALL be identified by a `period_id` that survives edits in the
sheet.

#### Scenario: New period recorded

- **WHEN** a period is recorded with a start date and an end date
- **THEN** it exists as one row in the sheet and the period list remains sorted by start date

#### Scenario: Same-day start recorded again

- **WHEN** a period is recorded whose start date equals the latest recorded start date and that period is still open
- **THEN** the existing row is updated instead of adding a duplicate

#### Scenario: Period identity after an edit

- **WHEN** a user changes a period's dates in the sheet without changing its `period_id`
- **THEN** the system treats it as the same period with corrected dates

### Requirement: Report current cycle phase

The system SHALL report the current cycle phase as one of menstrual, follicular,
ovulatory, or luteal, derived from the ovulation center and the configured
period length, and SHALL report no phase when no prediction exists.

#### Scenario: Menstrual phase

- **WHEN** the cycle day is within the configured period length
- **THEN** the reported phase is menstrual

#### Scenario: Luteal phase

- **WHEN** the cycle day is after the ovulatory window
- **THEN** the reported phase is luteal

#### Scenario: No phase without a prediction

- **WHEN** fewer than two usable completed cycles exist
- **THEN** the reported phase is unknown

### Requirement: Predict next period from history

The system SHALL predict the next period start date by applying the selected
prediction algorithm to the most recent usable recorded cycle lengths, and SHALL
report no prediction when there is insufficient history. The configured cycle
length SHALL NOT be used as a fallback.

#### Scenario: Enough history

- **WHEN** at least two usable completed cycles are recorded and the arithmetic-mean algorithm is selected
- **THEN** the predicted next start is the last period start plus the mean of the recent cycle lengths

#### Scenario: Weighted moving average

- **WHEN** the weighted-moving-average algorithm is selected and history exists
- **THEN** more recent cycles are weighted more heavily than older cycles in the prediction

#### Scenario: Insufficient history

- **WHEN** fewer than two usable completed cycles are recorded
- **THEN** the reported prediction is unknown

### Requirement: Predict next ovulation

The system SHALL provide the next predicted ovulation center date, its window,
and the number of days until it, and both values SHALL be available whenever a
prediction exists.

#### Scenario: Days until ovulation available

- **WHEN** a prediction exists
- **THEN** the days-until-ovulation value is a non-negative integer rather than an error

#### Scenario: Ovulation window exposed

- **WHEN** a prediction exists
- **THEN** the ovulation window start and end are available as attributes

#### Scenario: No ovulation without a prediction

- **WHEN** no prediction exists
- **THEN** the ovulation date and days-until-ovulation values are unknown

### Requirement: Report cycle statistics

The system SHALL report average cycle length, average period length, standard
deviations, total tracked cycles, and a prediction confidence value, and SHALL
degrade gracefully when fewer than two cycles exist. Cycle-length statistics
SHALL use the same usable six-cycle window as the prediction, and period-length
statistics SHALL use completed periods only.

#### Scenario: Single cycle tracked

- **WHEN** only one period is recorded
- **THEN** statistics report the configured lengths, zero deviations, and a tracked-cycle count of one

#### Scenario: Multiple cycles tracked

- **WHEN** multiple periods are recorded
- **THEN** average and standard-deviation values are computed from the recorded cycle lengths in the prediction window

#### Scenario: Open period excluded from period statistics

- **WHEN** the latest period has no end date
- **THEN** period-length statistics use completed periods only and do not fail

#### Scenario: Confidence reported

- **WHEN** a prediction exists
- **THEN** the statistics report a confidence value between 0 and 1 plus its band

### Requirement: Report elapsed cycle day

The system SHALL compute the current cycle day from the most recent period start
date, returning day 1 on the start date and counting forward one day at a time
without wrapping at the configured cycle length. When no period start is
recorded, the cycle day SHALL be unknown.

#### Scenario: Cycle day within a cycle

- **WHEN** the reference date is 2 days after a period start
- **THEN** the reported cycle day is 3

#### Scenario: Cycle day continues past the configured length

- **WHEN** the reference date is 33 days after a period start and no newer start is recorded
- **THEN** the reported cycle day is 34

### Requirement: Report days until the next period

The system SHALL report the number of days until the predicted next period,
counted as zero when the predicted date is today or already past, and SHALL
report whether the period is late together with how many days late it is.

#### Scenario: Days until a future period

- **WHEN** the predicted next period date is 3 days after the reference date
- **THEN** the reported days-until-period value is 3

#### Scenario: Late period is distinguishable from due today

- **WHEN** the predicted next period date is 4 days before the reference date
- **THEN** days-until-period is 0, the late flag is on, and the late count is 4

### Requirement: Report unknown without a prediction

The system SHALL report prediction-dependent entities as unknown, without zero
values, whenever no prediction exists.

#### Scenario: Fresh install

- **WHEN** no period has been recorded
- **THEN** cycle day, phase, predicted dates, and days-until values are unknown

#### Scenario: Prediction unavailable after a gap

- **WHEN** fewer than two usable cycles exist after the most recent long gap
- **THEN** the predicted dates and days-until values are unknown while the recorded history remains visible
