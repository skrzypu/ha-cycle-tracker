# Spec Delta

## Purpose

Clarifies that the prediction reports two ovulation positions: the windows of the
cycle that is running at the reference date (which may already have passed) and
the windows of the first ovulation that has not passed yet, which is what the
entities and the card present.

## MODIFIED Requirements

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
