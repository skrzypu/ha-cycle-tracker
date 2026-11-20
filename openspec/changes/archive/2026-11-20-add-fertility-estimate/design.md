# Design

## Context

See `proposal.md` for motivation and the `fertility-estimate` spec delta for the
behavior contract. The decision record is BDR-0004, section "Refined again on
2026-11-19". The product already derives a prediction and a `CycleStatistics`
object once per reference date in `domain/prediction.py:build_snapshot`, with a
population σ (`pstdev`) in `domain/statistics.py`, and exposes entities from
`coordinator.snapshot`. Settings are resolved options → data → default by
`_setting` in both `config_flow.py:81` and `coordinator.py:168`; options changes
already reload the entry via `__init__.py:async_reload_entry` (line 304). The
six-day fertile window and the two-cycle minimum live in `domain/windows.py` and
`cycle-prediction`; this change reuses them and must not modify them.

## Goals / Non-Goals

**Goals:**

- Compute the estimate as a pure, clock-free domain function fed by the existing
  snapshot; reuse σ, confidence and the fertile-window geometry rather than
  recomputing them.
- Gate a single new entity behind an opt-in option that needs no migration and
  leaves existing entries untouched.
- Keep all user-facing copy in translations, with a stable technical state
  vocabulary in the domain.

**Non-Goals:**

- No change to `cycle-prediction` requirements, its six-day window, the
  confidence formula, or the two-cycle rule.
- No new contraceptive promise, no per-day probability, no temperature or
  mucus input, no separate card or charts.
- No initial-setup toggle and no config migration.

## Decisions

**1. New pure domain module and frozen model.** Add `domain/fertility.py` with
`fertility_estimate(prediction, statistics, today) -> FertilityEstimate`, a
frozen dataclass, and a `FertilityState` string enum whose values are the stable
technical tokens `outside_estimated_fertile_window`,
`within_estimated_fertile_window`, `unknown`. The function takes a reference
date and never reads `date.today()`. Confidence, its band and the usable-cycle
count are copied from `CycleStatistics`/`Prediction`; σ comes from
`CycleStatistics.cycle_length_std_dev`. This mirrors the `Prediction` pattern in
`domain/models.py:92` and satisfies ADR-0001/0005/0006. Alternative: putting the
math on `Prediction` — rejected because it would blur the boundary between the
core promise and an optional presentation and would require touching
`cycle-prediction`.

**2. Margin and band derived, not configured.** `margin = max(2,
ceil(statistics.cycle_length_std_dev))`; bands are built from the existing
windows: current cycle `[fertile_start - margin, ovulation_center + margin]` and
next cycle `[next_ovulation.fertile[0] - margin, next_ovulation.ovulation_center
+ margin]`. The reference date is `within` if it lies in either band, `outside`
otherwise, `unknown` when there is no prediction or fewer than two usable
cycles. Bands are not clamped to the cycle start: they express uncertainty about
an ovulation that can fall near a boundary, and clamping would fake precision.
This reuses `OVULATION_LEAD_DAYS`/`FERTILE_LEAD_DAYS` from `domain/windows.py`
without changing them. Alternative: a configurable margin — rejected because
the decision specifies a derived value.

**3. Compute always, expose only when enabled.** `build_snapshot` gains a
`fertility: FertilityEstimate` field computed unconditionally (cheap and pure),
so the domain function needs no knowledge of the toggle. The sensor platform
(`sensor.py:async_setup_entry`) checks
`coordinator.get_enable_fertility_estimate()` and only adds
`FertilityEstimateSensor` when it is true; a disabled entry therefore has no
entity at all rather than an `unavailable` one. Alternative: gating computation
in the coordinator — rejected as needless coupling.

**4. Setting plumbing.** Add `CONF_ENABLE_FERTILITY_ESTIMATE` and
`DEFAULT_ENABLE_FERTILITY_ESTIMATE = False` to `const.py`, alongside the
`enable_notifications` pattern (line 17/32). Add the option to the options-flow
`init` schema (`config_flow.py:587-708`) with a `BooleanSelector`, defaulted via
`_setting(entry, key, DEFAULT_ENABLE_FERTILITY_ESTIMATE)`, next to
`CONF_HISTORY_WINDOW`; deliberately do not add it to `async_step_preferences`
(initial setup). Add `coordinator.get_enable_fertility_estimate()` using its
`_setting`. Existing entries without the key resolve to `False` with no
migration; the existing options-change reload handles toggling.

**5. Entity surface and copy separation.** `FertilityEstimateSensor` is a
`CoordinatorEntity`/`SensorEntity` like `CycleTrackerSensor`; it sets
`_attr_translation_key = "fertility_estimate"`, returns the enum value as its
state, and exposes base window, band, `margin_days`, `confidence`,
`confidence_band` and `usable_cycle_count` as attributes (new constants in
`const.py`, reusing `ATTR_CONFIDENCE_BAND`/`ATTR_USABLE_CYCLE_COUNT`). Add
`entity.sensor.fertility_estimate.state.*` keys to both `translations/en.json`
and `pl.json` with the exact PL labels from BDR-0004 and factual EN equivalents;
the option label goes in the options `data` map of both files. The domain holds
only tokens, never copy.

**6. Conditional card section.** Extend the card's `DEFAULT_ENTITIES`,
`CT_UNIQUE_SUFFIX` and `ENTITY_LABELS` maps (`cycle-tracker-card.js:5-44`) with
`fertility_estimate`, add a `_renderFertility()` invoked from the existing render
path (line ~1209), and hide the section when the entity is not tracked. Put the
labels and the exact symmetric disclaimer in the card's own text map, with the
uncertainty band beside the fact. The section is appended after the statistics
disclosure in the card template — `<details class="fertility-section">` follows
`<details class="stats-disclosure">` — so the order is fixed by the template and
neither the render logic nor the CSS changes. Alternative: always show the section —
rejected because it would render an empty block for the default-off majority.

The section is also a disclosure: the heading is a `<summary>` button with
`aria-expanded` and `aria-controls` that toggles the body on click and natively
on Enter/Space, collapsed by default, with the body hidden rather than deleted
so the fact, band and disclaimer stay in the product. It follows the card's
existing `stats-disclosure`/`stats-summary` pattern
(`cycle-tracker-card.js:531-553`, `931-932`) for the marker, cursor and
focus-visible treatment, and uses the native `<details>`/`<summary>` pair with
the explicit ARIA attributes kept in sync on `toggle`, because the contract
names them. Expanded state is deliberately not persisted — no `localStorage` and
no config — so a reload returns to collapsed; no new dependency.

## Risks / Trade-offs

- [Copy drifts into contraceptive wording] → keep copy only in translations and
  the card text map; add a test scanning new strings for the banned words and a
  test asserting the disclaimer text is present verbatim.
- [State-translation mapping depends on HA support] → verify the
  `translation_key`/`state` lookup with an entity test; the state itself remains
  a stable token even if a frontend cannot translate it.
- [Irregular cycles widen the band until few "outside" days remain] → this is
  the intended honest behavior from BDR-0004; do not narrow the margin.
- [Band crosses the cycle boundary] → accepted; document that the band is an
  uncertainty presentation, not a clamped geometric window.
- [Options reload briefly recreates entities] → existing reload mechanism is
  already used for other options; no new lifecycle path.

## Migration Plan

None: additive and default-off. `_setting` returns `False` for existing entries,
so no stored data changes. Rollback is to turn the option off and reload; the
entity disappears and the card section hides.

## Open Questions

- Whether a dedicated fertility card is wanted later is deferred; it does not
  affect this change, which only adds a section to the shipped card.
