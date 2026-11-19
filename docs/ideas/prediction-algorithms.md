# Idea: Prediction Algorithms

- **Status:** decided — recorded in [BDR-0004](../bdr/0004-prediction-is-a-window-not-a-date.md) on 2026-11-10
- **Problem:** the current prediction is two formulas applied to the last six
  cycle lengths, with an arbitrary ovulation offset and a hard-coded confidence.
  Nothing records why those choices were made, and the domain model is supposed
  to provide exactly what the algorithms need — so the algorithms have to be
  understood before the model is frozen.
- **Idea:** work through the prediction questions below, decide what the product
  should promise, then derive the model fields and the algorithm contracts from
  those answers.
- **Constraints / conflicts:** ADR-0005 (pure domain, testable without Home
  Assistant); the existing `cycle-tracking` spec already promises arithmetic mean
  and weighted moving average; the current sensor hard-codes
  `prediction_confidence: 0.5` (as of the decision — confidence is now computed;
  see "Current behavior" below).
- **Value:** one documented set of prediction and statistics contracts that the
  domain model and the product can rely on instead of re-deriving each choice.
- **Dependencies:**
  - ADR-0005 (pure domain, testable without Home Assistant) — known
  - BDR-0004 (the decision that records these answers) — known
- **Open questions:** the product gaps listed under "Still open (product)" —
  the all-history statistic (question 9) and the fertile-window wording
  (question 12).
- **Decision:** recorded in [BDR-0004](../bdr/0004-prediction-is-a-window-not-a-date.md)
  on 2026-11-10; see "Decided so far" below.

## Decided so far

- **Prediction output:** the next period date, an uncertainty window around it,
  and a fertile window. Not a single date alone.
- **Ovulation:** a window, not a single day, centered on **14 days before the
  predicted next period**.
- **Fertile window:** five days before ovulation through ovulation day (six days,
  asymmetric).
- **Uncertainty window:** ±1 standard deviation of the cycle lengths used.
- **Ovulation window:** ±2 days around the center (five days total).
- **Minimum history:** two completed cycles, but the uncertainty window has a
  lower bound (for example ±2 days) so it does not look more certain than it is.
  Before that, the prediction sensor is `unknown` — no settings-based fallback.
- **History window:** the last 6 cycles feed the prediction.
- **Algorithm set:** arithmetic mean, weighted moving average, and median, chosen
  by the user.
- **Outliers:** cycles outside 15–90 days are excluded from prediction only. The
  row stays in history and statistics and is flagged with a warning. The bounds
  are fixed by default with an advanced override in the options.
- **Confidence:** the number `min(1, 1 − σ/mean) × min(1, n/6)` plus a verbal
  band (low below 0.4, medium 0.4–0.7, high above 0.7). Exposed as an attribute
  of the statistics sensor.
- **Statistics inputs:** period-length statistics use completed periods only;
  cycle-length statistics use the same last 6 cycles as the prediction.
- **Phase boundaries:** derived from the ovulation window — menstrual while
  within the period length, ovulatory around the ovulation window, follicular
  before it, luteal after it.
- **Data gaps:** a gap longer than 90 days is missing data, not a cycle. It is
  excluded from prediction like an outlier and flagged, but stays in history.
- **Model shape:** a cycle is always derived from consecutive period starts, never
  stored. A period is `id`, `start`, optional `end`, optional `flow`, optional
  `notes`, `updated_at` — no `created_at` and no `source` in the domain.
- **Identity:** a UUID generated once at creation, stored as `period_id`. Editing
  a date keeps the identity.
- **Default algorithm:** weighted moving average; the user can switch to
  arithmetic mean or median.
- **Time:** predictions are pure functions with a reference date from a `Clock`
  port; nothing calls `date.today()`.
- **Confidence exposure:** an attribute of the statistics sensor, not a separate
  entity.
- **Late period:** when the predicted date passes without a new period, the
  sensor marks the period as late. The predicted date does not move on its own.
- **Invariants:** hard errors only for `end < start` and overlapping periods;
  everything else is a warning. No silent repair.
- **Migration:** none — there is no shipped data to migrate.

## Current behavior (facts, not decisions)

- `domain/strategies.py` has three strategies: `arithmetic_mean`,
  `weighted_moving_average` (weights 1..n, newest highest) and `median`.
- The coordinator uses the last 6 cycle lengths when at least 2 exist, otherwise
  falls back to the configured cycle length.
- A cycle length is the number of days between two consecutive period starts.
- Ovulation is computed as `last_start + cycle_length // 2`, repeated forward
  until it is not in the past.
- Phase boundaries: menstrual while `cycle_day <= period_length`; ovulatory
  within `cycle_length // 2 ± 1`; follicular before that; luteal after.
- Statistics use all recorded cycles; period length uses `end - start + 1` and
  fails for an open period.
- Confidence is computed (`confidence_score` and `confidence_band` in
  `domain/statistics.py`, called from `domain/prediction.py`) — there is no
  constant `0.5` on the sensor.
- Flow intensity is one of `spotting`, `light`, `medium`, `heavy`, defaulting to
  `medium` in the service schema.
- There is no migration concern: the integration has not shipped usable data.

## Open questions

### 1. What feeds a cycle length?

**Answered:** only completed cycles. A cycle length is start-to-start, so the
open period contributes nothing until the next start exists. The current cycle's
elapsed days are never treated as a length; when it runs past the window the
period is marked late (question 18) instead.

### 2. Outliers and bad data

**Answered:** cycles outside 15–90 days are excluded from prediction only. The
row stays in history and in statistics, and is flagged with a warning so the user
can fix a typo or accept a genuinely long cycle. The bounds are fixed by default,
with an advanced override in the options.

### 3. Minimum history

**Answered:** two completed cycles are enough to predict. Before that the sensor
is `unknown` — the configured cycle length is not used as a fake prediction. The
uncertainty window has a lower bound (for example ±2 days) because a standard
deviation from two samples is not credible on its own.

### 4. Window size

**Answered:** the last 6 cycles. Short enough to react to real change, long
enough for a usable standard deviation once the minimum history is met. Only
completed cycles count (question 1); gaps longer than 90 days are missing data
(question 14).

### 5. Algorithm set

**Answered:** three selectable strategies — arithmetic mean, weighted moving
average, and median. The median is added as the outlier-resistant option even
though prediction already excludes cycles outside 15–90 days. The default is
weighted moving average.

### 6. What is "confidence"?

**Answered:** a number in 0–1 from
`min(1, 1 − σ/mean) × min(1, n/6)`, where σ and mean come from the cycles used
and n is their count. It is exposed as an attribute of the statistics sensor,
together with a verbal band so the number is not read as precision it does not
have: low below 0.4, medium from 0.4 to 0.7, high above 0.7.

### 7. Ovulation basis and window center

**Answered:** the center is 14 days before the predicted next period.

### 8. Ovulatory window and phase boundaries

**Answered:** the phase boundaries are derived from the ovulation window.
Menstrual while the cycle day is within the period length, ovulatory around the
ovulation window, follicular before it, luteal after it. One source of truth for
phases and ovulation.

### 9. Statistics inputs

**Answered:** period-length statistics use completed periods only, so an open
period no longer breaks them. Cycle-length statistics use the same last 6 cycles
as the prediction.

Still open: whether statistics keep showing an all-history figure somewhere (for
example a lifetime average) or only the windowed one.

### 10. What the model must provide

**Answered:** a `Cycle` is never stored — it is always derived from consecutive
period starts. A period carries the minimal field set: `id`, `start`, optional
`end`, optional `flow`, optional `notes`, `updated_at`. No `created_at` and no
`source` in the domain; `source` belongs to the adapter. Identity is a UUID
generated at creation (question 15).

### 11. Determinism and time

**Answered:** predictions are pure functions of their inputs plus a reference
date supplied by a `Clock` port. No algorithm calls `date.today()`.

### 12. Fertile window definition

**Answered:** five days before ovulation through ovulation day, six days total.

How is it worded so it is not read as a contraceptive guarantee?

### 13. Uncertainty window width

**Answered:** ±1 standard deviation of the cycle lengths used. When there is no
deviation (a single cycle), the window collapses to the predicted date.

### 14. Data gaps

**Answered:** a gap longer than 90 days is missing data, not a cycle. It is
excluded from prediction the same way an outlier is, and the user is warned. The
history itself is untouched; there is no "new epoch" state.

The gap threshold is the same 90-day bound used for outliers, so there is one
number to explain and one place to override it.

### 15. Identity

**Answered:** a UUID generated once at creation and stored as `period_id`.
Editing a date keeps the identity, so the sheet row stays the same row.

### 16. Invariants

**Answered:** only two are hard errors — `end` before `start`, and overlapping
periods. Everything else (unusually long period, missing flow) is a warning.
The model never silently repairs user data.

### 17. Migration

**Answered:** none. The integration has not shipped usable data yet, so the old
`{start_date, end_date}` dictionaries are discarded rather than migrated.

## What this implies for the domain model

Derived from the answers above; this is the input to `domain-model.md`, not a
decision by itself.

- **Period**: `id` (UUID), `start`, `end | None`, `flow | None`,
  `notes | None`, `updated_at`.
- **Derived, never stored**: cycle length (start-to-start), the used cycle window
  (last 6), the filtered set (15–90 days), σ and mean, ovulation center and
  window, fertile window, uncertainty window, phase boundaries, confidence.
- **Prediction inputs**: the period list plus a reference date from `Clock` plus
  the configured algorithm name.
- **Prediction output**: next period date, uncertainty window, ovulation window,
  fertile window, confidence value and band, late flag, and a list of data
  warnings (outliers, gaps).
- **No `source` in the domain**: origin (HA, sheet) is an adapter concern.
- **No `created_at`**: `updated_at` is enough for the current requirements.
- **No migration path**: old dictionaries are dropped, so the adapter starts
  from an empty store.

## Still open (product)

- Whether an all-history statistic is shown next to the windowed one (question 9).
- How the fertile window is worded so it is not read as contraception
  (question 12). This is copy work and can wait for the card.

## Next step

Update `docs/ideas/domain-model.md` with these answers, close the questions it
inherits, and only then consider an ADR or a spec.
