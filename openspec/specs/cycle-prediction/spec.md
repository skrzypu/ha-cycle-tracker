# cycle-prediction Specification

## Purpose
Turns recorded periods and a reference date into a prediction: a next period
date, uncertainty, ovulation and fertile windows, a confidence value, a late
state, data warnings, cycle phases, and projected future cycle events.

## Requirements

### Requirement: Derive cycle lengths from period starts

The system SHALL derive a cycle length as the number of days between two
consecutive recorded period start dates, oldest first, and SHALL never store it.
Only consecutive starts count: a period still open contributes no length until
the next start is recorded.

#### Scenario: Three starts produce two lengths

- **WHEN** periods started on 2026-01-01, 2026-01-29 and 2026-02-26
- **THEN** the derived cycle lengths are 28 and 28 days, oldest first

#### Scenario: Open period contributes nothing

- **WHEN** the latest period started on 2026-03-26 and has no end date
- **THEN** it contributes no cycle length until another start is recorded

### Requirement: Exclude out-of-range cycles from prediction

The system SHALL exclude cycles shorter than the lower bound and longer than the
upper bound from prediction, using bounds supplied by configuration that default
to 15 and 90 days. Excluded cycles SHALL remain in history and statistics.

#### Scenario: Long cycle excluded with a narrowed upper bound

- **WHEN** the upper bound is configured to 60 days and the recorded cycle lengths are 28, 29, 75 and 30 days
- **THEN** prediction uses 28, 29 and 30 and reports an outlier warning for the 75-day cycle

#### Scenario: Short cycle excluded from prediction

- **WHEN** the recorded cycle lengths are 28, 10 and 29 days
- **THEN** prediction uses 28 and 29 and reports a warning for the 10-day cycle

### Requirement: Stop the history window at a long gap

The system SHALL treat a gap longer than 90 days between consecutive period
starts as missing data, SHALL exclude the cycle at that boundary from
prediction, and SHALL use only cycles recorded after the most recent such gap.
Earlier history SHALL remain available to statistics. The boundary cycle SHALL
be reported as a gap warning rather than an outlier warning.

#### Scenario: Window does not reach across a gap

- **WHEN** periods are recorded through 2026-02-26 and the next start is 2026-09-01
- **THEN** the 187-day boundary cycle is excluded and no earlier cycle is used for prediction

#### Scenario: Recovering after a gap needs new cycles

- **WHEN** the only period after a 187-day gap started on 2026-09-01
- **THEN** no prediction is available until two usable cycles exist after the gap

### Requirement: Select the last six usable completed cycles

The system SHALL filter cycles before selecting the history window, and SHALL
use at most the six most recent cycles that remain after filtering. An excluded
cycle SHALL NOT occupy a slot in the window.

#### Scenario: Filtering happens before the window

- **WHEN** the filtered cycle lengths are 27, 28, 29, 28, 30, 28, 31 and 29 days
- **THEN** prediction uses 29, 28, 30, 28, 31 and 29 (the six most recent) and ignores 27 and 28

#### Scenario: Window is shorter than six

- **WHEN** only three usable cycles remain after filtering
- **THEN** prediction uses all three

### Requirement: Require two usable cycles

The system SHALL produce no prediction when fewer than two usable completed
cycles remain after filtering, and SHALL NOT substitute the configured cycle
length.

#### Scenario: One usable cycle

- **WHEN** only one usable completed cycle exists
- **THEN** no prediction is produced

#### Scenario: Configured length is not a fallback

- **WHEN** no usable completed cycle exists and the configured cycle length is 28
- **THEN** no prediction is produced and the prediction date is unknown

### Requirement: Apply the selected prediction strategy

The system SHALL predict a cycle length by applying one of three selectable
strategies to the usable window: arithmetic mean, weighted moving average with
newer cycles weighted more heavily (weights 1 to n, oldest to newest), or median.
The strategy SHALL return whole days using round-half-up. The default strategy
SHALL be weighted moving average.

#### Scenario: Arithmetic mean

- **WHEN** the usable lengths are 26, 30 and 31 and arithmetic mean is selected
- **THEN** the predicted cycle length is 29 days

#### Scenario: Weighted moving average

- **WHEN** the usable lengths are 26 and 30 and weighted moving average is selected
- **THEN** the predicted cycle length is 29 days, because the newer cycle carries twice the weight

#### Scenario: Median with an even count

- **WHEN** the usable lengths are 26, 30, 31 and 27 and median is selected
- **THEN** the predicted cycle length is 29 days, the rounded mean of the two middle values

### Requirement: Predict the next period date

The system SHALL predict the next period start date as the most recent period
start plus the predicted cycle length. The predicted date SHALL NOT advance on
its own when the period does not arrive.

#### Scenario: Predicted date from the predicted length

- **WHEN** the latest start is 2026-11-01 and the predicted cycle length is 30 days
- **THEN** the predicted next period date is 2026-12-01

#### Scenario: Predicted date stays put when late

- **WHEN** the predicted next period date is 2026-12-01 and no start is recorded by 2026-12-06
- **THEN** the predicted next period date is still 2026-12-01

### Requirement: Report an uncertainty window

The system SHALL report the predicted period date with an uncertainty window of
plus and minus one standard deviation of the usable cycle lengths, treating them
as the whole set, with the standard deviation rounded up to whole days and the
half-width never below two days.

#### Scenario: Lower bound applies to a stable history

- **WHEN** the usable lengths are 28 and 28
- **THEN** the uncertainty window is plus and minus two days around the predicted date

#### Scenario: Wider window for variable cycles

- **WHEN** the usable lengths are 25, 32, 26 and 33
- **THEN** the standard deviation is about 3.5 days, so the window is plus and minus four days

### Requirement: Report an ovulation window

The system SHALL report an ovulation window centered on fourteen days before the
predicted next period date, spanning two days before through two days after the
center. These windows SHALL belong to the cycle running at the reference date, so
they MAY lie in the past, and the prediction SHALL ALSO report the windows of the
first ovulation whose center is on or after the reference date: the running
cycle's when it is still ahead, otherwise those of a following cycle derived by
advancing the predicted cycle length.

#### Scenario: Ovulation window for a 28-day prediction

- **WHEN** the predicted next period date is 2026-12-01 and the predicted cycle length is 28 days
- **THEN** the ovulation center is 2026-11-17 and the window is 2026-11-15 to 2026-11-19

#### Scenario: The running cycle's ovulation has already passed

- **WHEN** the predicted next period date is 2026-12-01, the predicted cycle length is 28 days and the reference date is 2026-11-20
- **THEN** the current-cycle ovulation center stays 2026-11-17 and the next ovulation center is 2026-12-15
- **AND** the next ovulation window is 2026-12-13 to 2026-12-17

### Requirement: Report a fertile window

The system SHALL report a fertile window from five days before the ovulation
center through the ovulation center, six days in total, and SHALL describe it as
an estimate that is not a contraceptive guarantee.

#### Scenario: Fertile window follows the ovulation center

- **WHEN** the ovulation center is 2026-11-17
- **THEN** the fertile window is 2026-11-12 to 2026-11-17

### Requirement: Report prediction confidence

The system SHALL report a confidence value between 0 and 1 computed as
`min(1, 1 - sigma / mean) * min(1, n / 6)`, where sigma and mean come from the
usable cycle lengths and n is their count, together with a band of low below
0.4, medium from 0.4 to 0.7, and high above 0.7.

#### Scenario: Two cycles score low

- **WHEN** the usable lengths are 28 and 28
- **THEN** confidence is about 0.33 and the band is low

#### Scenario: Four variable cycles score medium

- **WHEN** the usable lengths are 25, 32, 26 and 33
- **THEN** confidence is about 0.59 and the band is medium

#### Scenario: Six stable cycles score high

- **WHEN** six usable cycles are recorded with a standard deviation of one day and a mean of 28 days
- **THEN** confidence is about 0.96 and the band is high

### Requirement: Report data warnings

The system SHALL report a warning for every cycle excluded from prediction and
for every period missing a flow intensity, identifying the affected period, and
SHALL continue to produce a prediction when at least two usable cycles remain.

#### Scenario: Outlier reported and prediction continues

- **WHEN** one excluded cycle and two usable cycles exist
- **THEN** the prediction is produced and one outlier warning names the excluded period

#### Scenario: Gap reported

- **WHEN** a gap longer than 90 days separates two recorded periods
- **THEN** a gap warning names the period at the boundary

### Requirement: Report a late period

The system SHALL mark the prediction as late when the reference date is after
the predicted next period date and no period start on or after that date is
recorded, and SHALL report how many days late it is.

#### Scenario: Late by five days

- **WHEN** the predicted date is 2026-12-01, the reference date is 2026-12-06 and no newer start exists
- **THEN** the prediction is late and the late count is five days

#### Scenario: New start clears the late state

- **WHEN** a period starts on 2026-12-04 and the reference date is 2026-12-06
- **THEN** the prediction is not late

### Requirement: Derive cycle phases from the ovulation center

The system SHALL derive the phase of a date from an ovulation center fourteen
days before the next period start, using the actual next start for a completed
cycle and the predicted next period date for the current cycle. The phase SHALL
be menstrual while the cycle day is within the configured period length,
follicular before the ovulation window, ovulatory within the ovulation window,
and luteal after it.

#### Scenario: Default 28-day cycle

- **WHEN** the predicted cycle length is 28 days and the configured period length is 5 days
- **THEN** days 1 to 5 are menstrual, 6 to 12 follicular, 13 to 17 ovulatory and 18 to 28 luteal

#### Scenario: Completed cycle uses its actual next start

- **WHEN** a closed cycle started on 2026-01-01 and the next period started on 2026-01-29
- **THEN** its ovulation center is 2026-01-15, not a date derived from the current prediction

#### Scenario: No prediction means no phase

- **WHEN** fewer than two usable completed cycles exist
- **THEN** no phase is reported

### Requirement: Configured period length wins over the ovulation window

Where the configured period length reaches into the ovulation window, the system
SHALL report the menstrual phase for those days, start the ovulatory phase on the
day after the last menstrual day, and omit the follicular phase when no day
remains between the period and the ovulatory window. The ovulation window SHALL
be clipped to the cycle.

#### Scenario: Long period wins over the ovulation window

- **WHEN** the predicted cycle length is 21 days and the configured period length is 7 days
- **THEN** days 1 to 7 are menstrual, 8 to 10 ovulatory and 11 to 21 luteal, and no follicular phase occurs

### Requirement: Project future cycle events

The system SHALL project future cycle events from a prediction for a bounded
horizon, by stepping forward by the predicted cycle length, and SHALL expose a
predicted period event for each projected cycle plus its ovulation window and
fertile window. Projected events SHALL be derived from the prediction rather
than from the configured cycle length.

#### Scenario: Projected period uses the predicted length

- **WHEN** the predicted next period date is 2026-12-01 and the predicted cycle length is 30 days
- **THEN** the second projected period starts on 2026-12-31

#### Scenario: Windows projected with the period

- **WHEN** a period is projected for a cycle
- **THEN** its ovulation window and fertile window are projected with it

### Requirement: Prediction is deterministic

The system SHALL compute the prediction as a pure function of the recorded
periods, the configuration, and a reference date supplied by the caller, and
SHALL NOT read the current date or persist derived values.

#### Scenario: Same inputs produce the same prediction

- **WHEN** the same periods, configuration and reference date are supplied twice
- **THEN** both predictions are identical

#### Scenario: Reference date is respected

- **WHEN** the same history is evaluated with two different reference dates
- **THEN** the only values that differ are those that depend on the reference date, such as the late state
