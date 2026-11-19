---
id: BDR-0004
title: Prediction is a window, not a date
status: accepted
date: 2026-11-10
deciders: []
supersedes: null
superseded-by: null
related: ["ADR-0005"]
---

# BDR-0004: Prediction is a window, not a date

## Context

The product is health-adjacent. A single predicted date reads as a certainty
even when the user's cycles are irregular, and the current implementation
hard-codes `prediction_confidence: 0.5`, which communicates nothing about how
much the prediction can be trusted.

The product must be honest about uncertainty without becoming useless for
automations: a bare date is easy to automate against, but a range is only
useful if its shape and meaning are fixed.

## Decision

We will promise the next period date together with an uncertainty window, an
ovulation window, and a fertile window — never a bare date alone.

The rules that make up that promise:

- **Uncertainty window:** ±1 standard deviation of the cycle lengths used, with
  a lower bound of ±2 days. When there is no deviation, it collapses to the
  predicted date.
- **Ovulation window:** centered on the predicted next period minus 14 days,
  ±2 days.
- **Fertile window:** five days before ovulation through ovulation day, six days
  total and asymmetric.
- **Phase boundaries:** derived from the ovulation window — menstrual while
  within the period length, ovulatory around the ovulation window, follicular
  before it, luteal after it.
- **History:** the last N completed cycles, where N is the configurable shared
  window (6–24; see the 2026-11-19 refinement). A cycle is start-to-start.
- **Minimum history:** 2 completed cycles. Before that the prediction sensor is
  `unknown`; there is no fallback to the configured cycle length.
- **Outliers:** cycles outside the 15–90 day range are excluded from prediction
  only. They stay in history and statistics and produce a warning. The bounds
  are fixed by default, with an advanced override.
- **Data gaps:** a gap longer than 90 days is missing data, not a cycle.
- **Algorithms:** arithmetic mean, weighted moving average (the default), and
  median, user-selectable.
- **Confidence:** `min(1, 1 − σ/mean) × min(1, n/N)`, where N is the configured
  window, exposed as an attribute of the statistics sensor with bands low < 0.4,
  medium 0.4–0.7, high > 0.7.
- **Late period:** when the predicted date passes without a new period, the
  sensor marks it late. The predicted date does not move on its own.
- **Wording:** must not read as a contraceptive guarantee. The exact copy is
  deferred to the card work.

Refined on 2026-11-13 in the review of `openspec/changes/add-cycle-prediction/`,
amended in place rather than superseded because the commitment is unchanged. The
following rules take precedence where the wording above is less specific.

- **Filter before window.** Out-of-range cycles and the cycle at a gap boundary
  are removed first, then the N most recent usable cycles are taken, where N is
  the configured shared window. An excluded cycle does not occupy a window slot.
- **Gap truncates the window.** The window stops at the most recent gap longer
  than 90 days: only cycles recorded after it feed prediction, at most N.
  Earlier cycles do not influence the prediction or the windowed average — a
  long break describes a different physiological state, so averaging across it
  would fake precision. They remain in recorded history and contribute only to
  the lifetime average added on 2026-11-19.
- **Population σ, ±2 floor.** Sigma is the population standard deviation of the
  usable lengths, treated as the whole set. Half-width is
  `max(2, ceil(sigma))`, so the ±2-day floor holds even at σ = 0; this replaces
  the earlier "collapses to the predicted date" wording.
- **Rounding and bounds.** Strategy results are rounded half-up, not with
  Python's banker's rounding. Window bounds are expanded (`ceil`/`floor`) so a
  window is never narrower than the data.
- **Phases from the ovulation centre.** Phase boundaries derive from a centre 14
  days before the next period start: the actual next start for a completed
  cycle, the predicted date for the current cycle.
- **Period length wins.** When the configured period length reaches into the
  ovulation window, those days are menstrual, the ovulatory phase starts after
  the last menstrual day, and no follicular phase is reported if no day remains.
  If nothing remains of the ovulatory window, there is no ovulatory phase.
- **Frozen prediction.** A late period does not move the predicted date. Future
  calendar events are projected from that frozen prediction by stepping forward
  by the predicted cycle length.
- **Two usable cycles.** Below two, prediction entities report `unknown`, phase
  is unknown, and only the elapsed cycle day remains. After a long gap the user
  needs two new cycles before prediction returns; the message says that rather
  than implying data was lost.
- **Confidence describes the data.** It comes from the usable data set, not the
  chosen strategy: switching algorithm changes the date but not the confidence.
- **Days until and cycle day.** `days_until_period` reads 0 when the period is
  due or late; the late flag and late-day count carry the distinction. Cycle day
  is an elapsed count and does not wrap at the configured length.

Refined on 2026-11-19 in response to I-013
(`docs/ideas/prediction-configurability.md`), amended in place rather than
superseded because this generalizes the history window without changing the
commitment: prediction is still a window, not a date, and the core promise —
uncertainty, ovulation and fertile windows, late period, phases, and the
two-cycle minimum — stands. The following rules take precedence where the
wording above is less specific.

- **One shared configurable window N.** A single setting in the config-entry
  options (ADR-0011), read through its resolver, feeds both prediction and
  cycle-length statistics; there is no service to change it. Range 6–24. New
  config entries store 12 in `entry.data`; existing ones fall back to
  `DEFAULT_HISTORY_WINDOW = 6`. No migration. "At most N" above means this
  number, not a fixed six.
- **Confidence denominator follows N.** The existing formula
  `min(1, 1 − σ/mean) × min(1, n/N)` already tracks the window through
  `target=config.history_window` in `domain/statistics.py` and
  `domain/prediction.py`; N replaces the literal 6 in prose. The bands stay
  low < 0.4, medium 0.4–0.7, high > 0.7.
- **Two-cycle minimum unchanged.** Prediction still needs two completed cycles.
  The 6-cycle floor is the lower bound of the setting and a cap on how many
  cycles the window uses, not a requirement on data: a user with 2–5 completed
  cycles still gets a prediction.
- **Lifetime cycle-length average added.** The statistics sensor keeps the
  windowed average and gains one additional lifetime average computed from all
  in-range cycles in recorded history: outlier cycles (outside 15–90 days) are
  excluded, while cycles before the most recent long gap are included. It is one
  extra statistic — not a chart and not a second window.
- **Outlier wording resolved: exclusion.** BDR-0004 above says outliers "stay in
  history and statistics", while `docs/guide/algorithms.md` says they are
  "excluded from prediction and from the cycle-length statistics". The latter
  wins: outliers are excluded from both cycle-length averages. They stay in
  recorded history and keep their warning. This closes the conflict in favour
  of exclusion.
- **Both averages on the existing card.** The windowed and the lifetime average
  appear as two labelled rows in the statistics section of the shipped Lovelace
  card (`cycle-tracker-card.js`, `_renderStatistics`); there is no separate card
  for now. Charts remain I-015 and a separate statistics card is parked as I-019.

Two consequences deserve prose. On a 28-day cycle the ovulation centre falls on
**cycle day 15** (day 1 is the start), not day 14 — the 14 counts backwards from
the next period. And the calendar is a projection of the frozen prediction, not
a second prediction.

The windows sit on the cycle as follows (illustrative 28-day cycle):

```mermaid
gantt
    title Prediction windows (illustrative 28-day cycle)
    dateFormat  YYYY-MM-DD
    axisFormat  %d %b
    section Fertility
    Ovulation centre          :milestone, 2026-11-15, 0d
    Ovulation window (±2)     :crit, 2026-11-13, 5d
    Fertile window            :active, 2026-11-10, 6d
    section Next period
    Next period (predicted)   :milestone, 2026-11-29, 0d
    Uncertainty (±1σ, min ±2) :2026-11-27, 5d
```

Ovulation centre sits 14 days before the predicted next period; the fertile
window runs the five days before ovulation through ovulation day; the
uncertainty window is ±1 standard deviation of the cycle lengths used, floored
at ±2 days. Dates are illustrative; real values come from the user's history.

In scope: what the product promises to show and how each window is derived, plus
the one lifetime cycle-length average added on 2026-11-19.
Out of scope: the implementation structure, the exact card copy, charts (I-015),
a separate statistics card (I-019), and any other all-history statistic beyond
the prediction window.

## Alternatives considered

| Alternative | Why not |
|---|---|
| A single date | Presents false certainty on irregular cycles and hides that the prediction is an estimate. |
| A single date plus a range, but no fertile window | Keeps ovulation and fertility implicit, so the product cannot answer the question users actually ask. |
| Ovulation as half the cycle length | Has no physiological basis and contradicts the 14-days-before-next-period model. |
| A symmetric fertile window (ovulation ±2 days) | The fertile window is not symmetric around ovulation; five days before through ovulation day is the intended shape. |
| Predicting immediately from the configured cycle length | Produces a confident-looking prediction with no user data behind it; `unknown` is more honest. |
| Keeping the constant confidence | A fixed 0.5 says nothing and cannot improve as history grows. |
| Moving the predicted date forward each day | Hides a late period instead of reporting it, and makes automations drift silently. |

## Expected impact

- **Users:** a more honest product. Users who expect a single date need the
  range explained, and the card becomes more complex.
- **Revenue / cost:** no direct revenue impact. The cost is additional sensor
  attributes and card work; estimates are unknown.
- **Operations / support:** more values to document and explain, especially the
  uncertainty window, the confidence bands, and the outlier warning.
- **Risk / compliance:** the fertile window must not be worded as
  contraception. Confidence now means something and must stay explainable, or
  it becomes another opaque number.

## Evidence

- `docs/ideas/prediction-algorithms.md` — records the answers this decision
  formalizes: prediction output, ovulation basis, fertile window, uncertainty
  window, minimum history, algorithm set, outliers, data gaps, confidence, and
  late periods.
- Current behavior: `prediction.py` implements only arithmetic mean and
  weighted moving average; the coordinator falls back to the configured cycle
  length below 2 cycles; `prediction_confidence` is the constant `0.5`.
- `docs/adr/0005-solid-and-clean-architecture.md` — prediction strategies and
  the `Clock` port constrain how these rules are implemented.
- `openspec/changes/add-cycle-prediction/` — the change that implements these
  rules; its design and `cycle-prediction` spec record the filter order, phase
  derivation, frozen date, and projection split.
- `docs/guide/algorithms.md` — the user-facing derivation the sensors must
  match.

Assumption: the 15–90 day outlier bounds and the 90-day gap threshold are
acceptable defaults for the target users. No usage data or user counts are
available to validate them.

## Follow-up

- [ ] Implement the prediction outputs and rules in the domain model.
- [ ] Add the confidence value and band to the statistics sensor attributes.
- [ ] Define the card copy for the range, the fertile window, and the late
      state, ensuring it does not read as a contraceptive guarantee.
- [ ] Add the advanced outlier-bound override to the options flow.
- [ ] Derive phases from the ovulation centre, using the actual next start for a
      completed cycle, and document that a 28-day cycle puts the centre on
      cycle day 15.
- [ ] Split projection from prediction: project calendar events from the frozen
      prediction by stepping forward by the predicted cycle length.
- [x] Align `docs/guide/algorithms.md` with the zero-deviation case: the window
      stays at ±2 days rather than collapsing.
- [ ] Revisit this record if user feedback shows the windows are too wide to
      automate against or too narrow to be honest.
- [ ] Add the shared window N to the config-entry options through ADR-0011's
      resolver (range 6–24; store 12 in `entry.data` for new entries, fall back
      to `DEFAULT_HISTORY_WINDOW = 6` for existing ones, no migration; no
      service).
- [ ] Generalize the confidence denominator to N, add the lifetime cycle-length
      average, and render both averages as labelled rows in
      `cycle-tracker-card.js` `_renderStatistics`.
- [ ] Update downstream artifacts to match the configured window and the
      exclusion wording — without editing this record again:
      `openspec/specs/cycle-prediction/spec.md` requirements "Select the last six
      usable completed cycles" and "Report prediction confidence",
      `docs/guide/algorithms.md`, and code docstrings.
