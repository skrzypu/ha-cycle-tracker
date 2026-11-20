# Proposal

## Why

Real recorded data exposed a presentation bug: while the reference date sits in
the gap between two estimated windows, the estimate shows only the upcoming
band. `domain/fertility.py:98-101` discards `current_band` in the `outside`
state and substitutes `next_band`, so the `margin_band` attribute and the card
report half of the truth — the user cannot see the window they have just left.
The user decided the gap must present both edges, and omit an edge only when it
genuinely does not exist.

## What Changes

- Add two fields to the fertility estimate model: `previous_margin_band` (the
  margin band of the cycle that has just passed) and `next_margin_band` (the
  margin band of the upcoming cycle), each a `(date, date)` pair or `None`.
- Populate both fields from the prediction the snapshot already builds — no new
  cycle projection. The previous edge is the current cycle's band and exists
  only when that band ends before the reference date; the next edge is the band
  of `Prediction.next_ovulation` and exists only when it starts after the
  reference date. When `next_ovulation` is the running cycle, the previous edge
  is absent and SHALL be omitted rather than duplicated or fabricated.
- Expose the two fields as `previous_margin_band` and `next_margin_band` entity
  attributes, each an ISO date pair or `null`, alongside the existing
  attributes, which keep their current meaning.
- In the card's `outside` state, render every available labelled band —
  „poprzedni pas szacunku" and/or „następny pas szacunku" — instead of the
  single unlabelled band. One available edge renders one line; no edge renders
  none. The `within` and `unknown` states keep their current rendering.
- Keep the existing margin geometry (`max(2, ceil(sigma))`), the six-day window,
  the classification thresholds, the copy ban and the BDR-0004 disclaimer
  unchanged.
- Update the shipped card, both OpenDesign prototype files and the prototype
  copies inside the `open-design` container.
- Plan the ADR-0016 patch bump `0.2.6` → `0.2.7` in
  `custom_components/cycle_tracker/manifest.json` and the matching
  `README.md` `?v=0.2.7` example URL.

## Capabilities

### New Capabilities

- `fertility-gap-bands`: the both-edges view of the estimated fertility gap —
  how the previous and next margin bands are derived from the existing
  prediction, when an edge is omitted, how they are exposed on the
  `fertility_estimate` entity, and how the card presents them in the `outside`
  state without changing the `within` or `unknown` states.

### Modified Capabilities

- None. The `fertility-estimate` spec keeps its requirements: the margin
  formula, band geometry, state classification, entity option and copy rules
  are untouched. This change only adds the missing previous edge and the
  two-edge presentation in the gap. The `cycle-prediction` spec is also
  untouched.

## Impact

- Code: `domain/fertility.py` (model fields and gap-edge derivation),
  `const.py` (two attribute-name constants), `sensor.py`
  (`FertilityEstimateSensor.extra_state_attributes`), and
  `www/cycle-tracker-card.js` (`FERTILITY_TEXT`, `_renderFertility()`).
- Tests: new domain cases for both edges, a single edge and the unchanged
  `within`/`unknown` payloads; entity cases for the two new attributes; card
  and prototype checks; the full suite and pre-commit at the end.
- Artifacts: `/tmp/opencode/cycle-tracker-fertility-prototype-light.html` and
  `-dark.html`, copied into the `open-design` container project
  `c4c1e720-2026-4b11-9a20-c4c1e720ca2d` as `index.html` and `dark.html`.
- Release: `manifest.json` version `0.2.6` → `0.2.7` and the `README.md`
  example resource URL `?v=0.2.7`, per ADR-0016 (planned, not executed by the
  planning change).
- Compatibility: additive. Existing attributes and both unchanged states keep
  their values and rendering; only the `outside` state gains information.
