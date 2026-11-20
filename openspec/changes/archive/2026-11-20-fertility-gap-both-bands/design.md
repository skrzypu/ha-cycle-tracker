# Design

## Context

See `proposal.md` for motivation and `specs/fertility-gap-bands/spec.md` for the
behavior contract. `domain/fertility.py` already computes two unclamped bands on
every estimate: `current_band` from `Prediction.fertile` / `ovulation_center`
(running cycle, possibly in the past) and `next_band` from
`Prediction.next_ovulation`. `domain/prediction.py:88-94` advances
`next_ovulation` to the first cycle whose ovulation centre is not before the
reference date, so the two bands already bracket a date in the gap. The
`outside` branch currently discards the earlier band, which is the whole bug.
The entity serialises one `margin_band`; the card's `_renderFertility()` renders
that single unlabelled band. No new prediction, projection or setting is needed.

## Goals / Non-Goals

**Goals:**

- Keep both bracketing bands on the frozen estimate, omitting an edge only when
  the available data does not contain it.
- Preserve every existing state token, attribute value and card rendering for
  `within` and `unknown`, so the change is additive for consumers.
- Keep the domain function pure and the user-facing copy factual and unchanged
  apart from the two new edge labels.

**Non-Goals:**

- No change to the margin formula, the six-day fertile window, the two-cycle
  minimum, the state classifier or `cycle-prediction`.
- No cycle projection backwards or forwards: an edge that would require a cycle
  the prediction does not supply stays absent.
- No change to the options flow, the calendar or the translations for existing
  state labels.

## Decisions

**1. Two new fields on the frozen model.** `FertilityEstimate` gains
`previous_margin_band: tuple[date, date] | None` and
`next_margin_band: tuple[date, date] | None`. Both are filled inside the existing
`fertility_estimate()` from the bands it already builds; the function keeps its
`(prediction, statistics, today)` signature, reads no clock and persists nothing
(ADR-0001/0005/0006). Alternative: return a list of bands — rejected because it
would change the public shape and make the "previous/next" meaning implicit.

**2. Edge presence rules.** Edges are populated only in the `outside` state. The
previous edge is `current_band` when its end is strictly before `today`; the next
edge is `next_band` when its start is strictly after `today`. When
`next_ovulation` is the running cycle, its band has not ended, so the previous
edge is absent — never duplicated from the next edge. In `within` and `unknown`
both edges are `None`, leaving those payloads byte-identical. Alternative: always
populate both edges and let the card hide them — rejected because it would change
the attributes of two states the spec declares unchanged.

**3. Existing `margin_band` stays as it is.** In `outside` it continues to carry
`next_band`, so automations written against the archived change keep working.
The new attributes are additive; the card uses them for the two-edge view instead
of the single unlabelled band. Alternative: repurpose `margin_band` as the
previous edge — rejected as a breaking change with no benefit to the user.

**4. Entity surface.** Add `ATTR_PREVIOUS_MARGIN_BAND` and
`ATTR_NEXT_MARGIN_BAND` to `const.py` and serialise the pairs with the existing
`_iso_window()` helper in `sensor.py`, yielding ISO pairs or `None`. Alternative:
a single combined attribute — rejected because the spec asks for two named
fields and a missing edge must be distinguishable as `null`.

**5. Card presentation.** Extend `FERTILITY_TEXT` with two factual labels
(„poprzedni pas szacunku", „następny pas szacunku"). In `_renderFertility()` the
`outside` branch renders one labelled line per available edge using
`_formatFertilityBand()`; `within` keeps its current single band and `unknown`
keeps no band. The disclaimer and the copy ban stay verbatim. Alternative: always
render two lines — rejected because an absent edge must produce no empty line.

**6. Days since the previous band.** The frozen estimate gains
`previous_band_days_ago: int | None`, computed in the `outside` branch as
`(today - current_band[1]).days` only when the previous edge exists; it is `None`
otherwise and in `within`/`unknown`. It travels to the entity as
`previous_band_days_ago` and the card's previous-edge line appends
„zakończył się N dni temu" beside the band dates. This stays a pure derivation
from the caller's reference date (no clock read). Alternative: compute it in the
card from the ISO end date — rejected because the domain already owns the
reference date and the entity should expose the value to automations too.
Copy stays factual (no banned words) and the disclaimer is unchanged.

**7. Release mechanics.** Per ADR-0016 the manifest patch is bumped `0.2.6` →
`0.2.7` and the `README.md` example `?v=` follows, as a task of this change. The
OpenDesign prototype copies in `/tmp/opencode/` and in the running `open-design`
container project `c4c1e720-2026-4b11-9a20-c4c1e720ca2d` are updated with
`docker cp`; that directory exists and is served over HTTP on port 7456. After
archive, the 0.2.7 package is rebuilt with the `ha-package` skill.

## Risks / Trade-offs

- [A late period leaves both bands in the past] → `next_ovulation` is advanced
  by `prediction.py` until its centre is not before `today`, so the next edge
  still exists; the previous edge may be absent and is omitted.
- [Both edges absent] → the card renders no band line; the state fact and the
  disclaimer remain, so the section is never empty.
- [Copy drifts into contraceptive wording] → only the two new labels are added;
  keep them factual and assert the banned words never appear.
- [Automations depend on the old single band] → existing attributes and their
  values are unchanged; only two new attributes appear.
- [HACS/card cache hides the fix] → bump the patch version and the `?v=` example
  in the same change, then rebuild the package after archive.

## Migration Plan

None for stored data: the new fields are computed on read, additive to the
snapshot and the entity. Rollback is to revert the change and reinstall the
previous package; no migration or persistence is involved.

## Open Questions

None.
