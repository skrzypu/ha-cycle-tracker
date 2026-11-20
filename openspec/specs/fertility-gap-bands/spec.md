# fertility-gap-bands Specification

## Purpose

Presents both edges of the estimated fertility gap — the band the reference
date has just left and the band it is approaching — so a date outside the
estimated windows is never described by only half of the available evidence.

## Requirements

### Requirement: Report both gap edges in the outside state

The system SHALL report two gap edges when the reference date is outside both
estimated bands: the current cycle's margin band as the previous edge and the
margin band of the prediction's next ovulation as the next edge. Both SHALL use
the existing unclamped band geometry and the existing margin, and SHALL be
derived from the prediction the snapshot already provides.

#### Scenario: Reference date between two bands

- **WHEN** the current cycle's ovulation centre is 2026-11-15, the next ovulation centre is 2026-12-13, the margin is 2 days and the reference date is 2026-11-20
- **THEN** the previous edge is 2026-11-08 to 2026-11-17 and the next edge is 2026-12-06 to 2026-12-15

#### Scenario: No additional cycle is projected

- **WHEN** the prediction supplies the current cycle and its next ovulation
- **THEN** the two edges are exactly those cycles' margin bands and no later cycle is considered

### Requirement: Omit a gap edge that does not exist

The system SHALL omit an edge rather than fabricate it: the previous edge SHALL
be absent when the current cycle's band has not ended before the reference
date, and the next edge SHALL be absent when the next band does not start after
it. An absent edge SHALL NOT be replaced by duplicating the other edge.

#### Scenario: The running cycle is already the next band

- **WHEN** the current cycle's ovulation centre is 2026-11-15, the margin is 2 days and the reference date is 2026-11-01, so the next ovulation is the running cycle
- **THEN** no previous edge is reported and the next edge is 2026-11-08 to 2026-11-17

#### Scenario: An absent edge stays absent

- **WHEN** only the next edge exists
- **THEN** the previous edge remains absent and is not copied from the next edge

### Requirement: Keep the within and unknown states unchanged

The system SHALL keep the `within_estimated_fertile_window` and `unknown` states
unchanged: their state token, base fertile window, margin band, margin days,
confidence, confidence band and usable-cycle count SHALL keep their current
values, and both gap edges SHALL be absent in those states.

#### Scenario: Within the estimated window

- **WHEN** the reference date falls inside the current cycle's margin band
- **THEN** the state is `within_estimated_fertile_window`, the margin band is that band, and both gap edges are absent

#### Scenario: Unknown estimate

- **WHEN** fewer than two usable completed cycles exist
- **THEN** the state is `unknown`, no window or band is reported, and both gap edges are absent

### Requirement: Expose both gap edges on the fertility entity

The system SHALL expose `previous_margin_band` and `next_margin_band` on the
`fertility_estimate` entity as inclusive ISO date pairs, or `null` when the edge
is absent. The existing attributes SHALL keep their names, values and meanings
in every state.

#### Scenario: Both edges exposed

- **WHEN** the state is `outside_estimated_fertile_window` and both edges exist
- **THEN** `previous_margin_band` and `next_margin_band` each contain an ISO start and end date, and the existing attributes are unchanged

#### Scenario: Absent edge exposed as null

- **WHEN** the state is `outside_estimated_fertile_window` and only the next edge exists
- **THEN** `previous_margin_band` is `null` and `next_margin_band` contains the ISO date pair

### Requirement: Present every available edge on the card

The card SHALL present each available gap edge in the `outside` state with a
factual label — „poprzedni pas szacunku" and „następny pas szacunku" — one line
per available edge and no line when no edge exists. The `within` and `unknown`
rendering, the copy ban and the BDR-0004 disclaimer SHALL remain unchanged.

#### Scenario: Two labelled edges

- **WHEN** the card renders the `outside` state with both edges
- **THEN** it shows a „poprzedni pas szacunku" line and a „następny pas szacunku" line, each with its dates, and the unchanged symmetric disclaimer

#### Scenario: One labelled edge

- **WHEN** the card renders the `outside` state with only the next edge
- **THEN** it shows only the „następny pas szacunku" line and no empty previous line

#### Scenario: Copy stays factual

- **WHEN** the card renders either available edge
- **THEN** none of „bezpieczny", „dni bezpieczne", „możesz" or „ryzyko zajścia" appears in the rendered copy

### Requirement: Report how long ago the previous band ended

In the `outside_estimated_fertile_window` state, when a previous edge exists,
the system SHALL report a whole number of days from that edge's inclusive end
date to the reference date, so the user can tell how long ago it ended without
computing the distance. The value SHALL be absent when no previous edge exists
and in the `within` and `unknown` states. It SHALL be derived from the reference
date already supplied to the estimate and SHALL NOT read the clock.

#### Scenario: Previous band ended three days ago

- **WHEN** the previous edge ends on 2026-11-17 and the reference date is 2026-11-20
- **THEN** the reported value is 3 days

#### Scenario: No previous edge

- **WHEN** only the next edge exists, or the state is `within` or `unknown`
- **THEN** no days-ago value is reported

### Requirement: Compute the gap edges deterministically

The system SHALL compute both gap edges as part of the pure estimate from the
prediction, statistics and reference date supplied by the caller, and SHALL NOT
read the current date or persist derived values.

#### Scenario: Same inputs produce the same edges

- **WHEN** the same prediction, statistics and reference date are supplied twice
- **THEN** both estimates report identical gap edges

#### Scenario: Reference date changes edge availability

- **WHEN** the same history is evaluated on a date inside a band and on a date in the following gap
- **THEN** the first evaluation reports no gap edges and the second reports the edges that exist for that date, while each band's geometry stays fixed
