# Spec Delta

## Purpose

Keeps the cycle-tracking contract accurate now that recorded periods come from
the configured Google Sheet and are identified by a stable row identifier.

## MODIFIED Requirements

### Requirement: Record menstrual periods

The system SHALL treat the configured Google Sheet as the source of recorded
periods, SHALL persist each period with an inclusive start date and an optional
end date, and SHALL keep records ordered by start date.

Each period SHALL be identified by a `period_id` that survives edits in the
sheet.

#### Scenario: New period recorded

- **WHEN** a period is recorded with a start date and an end date
- **THEN** it exists as one row in the sheet and the period list remains sorted
  by start date

#### Scenario: Same-day start recorded again

- **WHEN** a period is recorded whose start date equals the latest recorded start
  date and that period is still open
- **THEN** the existing row is updated instead of adding a duplicate

#### Scenario: Period identity after an edit

- **WHEN** a user changes a period's dates in the sheet without changing its
  `period_id`
- **THEN** the system treats it as the same period with corrected dates
