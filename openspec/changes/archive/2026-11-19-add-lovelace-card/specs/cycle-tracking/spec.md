# Spec Delta

## Purpose

Makes the ovulation entities show the next ovulation that has not passed instead
of the running cycle's window, which is in the past for most of the luteal phase.

## MODIFIED Requirements

### Requirement: Predict next ovulation

The system SHALL provide the next predicted ovulation center date, its window,
and the number of days until it, and both values SHALL be available whenever a
prediction exists. The reported ovulation SHALL be the first one whose center is
on or after the reference date, so the days-until value SHALL be measured to that
ovulation and SHALL NOT be clamped to zero once the running cycle's window has
passed.

#### Scenario: Days until ovulation available

- **WHEN** a prediction exists and the running cycle's ovulation is still ahead
- **THEN** the days-until-ovulation value is a non-negative integer counting to that ovulation

#### Scenario: Ovulation window exposed

- **WHEN** a prediction exists
- **THEN** the ovulation window start and end of that upcoming ovulation are available as attributes

#### Scenario: The running cycle's ovulation already passed

- **WHEN** a prediction exists, the reference date is 2026-11-20 and the running cycle's ovulation center is 2026-11-17
- **THEN** the reported ovulation center is the following cycle's 2026-12-15 and days-until-ovulation is 25

#### Scenario: No ovulation without a prediction

- **WHEN** no prediction exists
- **THEN** the ovulation date and days-until-ovulation values are unknown
