# Spec Delta

## Purpose

Tracks recorded menstrual cycles and derives current cycle state, upcoming period and ovulation predictions, and cycle statistics that the integration exposes to Home Assistant.

## ADDED Requirements

### Requirement: Record menstrual periods
The system SHALL persist each recorded period with an inclusive start date and end date, and SHALL keep records ordered by start date.

#### Scenario: New period recorded
- **WHEN** a period is recorded with a start date and an end date
- **THEN** both dates are stored and the period list remains sorted by start date

#### Scenario: Same-day start recorded again
- **WHEN** a period is recorded whose start date equals the latest recorded start date
- **THEN** the existing record is updated instead of adding a duplicate

### Requirement: Report current cycle day
The system SHALL compute the current cycle day from the most recent period start date and the configured cycle length, returning day 1 on the start date and wrapping back to day 1 at the start of the next cycle.

#### Scenario: Cycle day within a cycle
- **WHEN** the reference date is 2 days after a period start with a 28-day cycle length
- **THEN** the reported cycle day is 3

#### Scenario: Cycle day wraps
- **WHEN** the reference date is exactly one cycle length after a period start
- **THEN** the reported cycle day is 1

### Requirement: Report current cycle phase
The system SHALL report the current cycle phase as one of menstrual, follicular, ovulatory, or luteal, derived from the current cycle day, the configured period length, and the configured cycle length.

#### Scenario: Menstrual phase
- **WHEN** the cycle day is within the configured period length
- **THEN** the reported phase is menstrual

#### Scenario: Luteal phase
- **WHEN** the cycle day is after the ovulatory window
- **THEN** the reported phase is luteal

### Requirement: Predict next period from history
The system SHALL predict the next period start date by applying the selected prediction algorithm to the most recent recorded cycle lengths, and SHALL fall back to the configured cycle length only when there is insufficient history.

#### Scenario: Enough history
- **WHEN** at least two completed cycles are recorded and the arithmetic-mean algorithm is selected
- **THEN** the predicted next start is the last period start plus the mean of the recent cycle lengths

#### Scenario: Weighted moving average
- **WHEN** the weighted-moving-average algorithm is selected and history exists
- **THEN** more recent cycles are weighted more heavily than older cycles in the prediction

#### Scenario: Insufficient history
- **WHEN** fewer than two completed cycles are recorded
- **THEN** prediction falls back to the configured cycle length

### Requirement: Predict next ovulation
The system SHALL provide the next predicted ovulation date and the number of days until it, and both values SHALL be available whenever a last period start is recorded.

#### Scenario: Days until ovulation available
- **WHEN** a last period start is recorded
- **THEN** the days-until-ovulation value is a non-negative integer rather than an error

### Requirement: Report cycle statistics
The system SHALL report average cycle length, average period length, standard deviations, total tracked cycles, and a prediction confidence value, and SHALL degrade gracefully when fewer than two cycles exist.

#### Scenario: Single cycle tracked
- **WHEN** only one period is recorded
- **THEN** statistics report the configured lengths, zero deviations, and a tracked-cycle count of one

#### Scenario: Multiple cycles tracked
- **WHEN** multiple periods are recorded
- **THEN** average and standard-deviation values are computed from the recorded cycle lengths
