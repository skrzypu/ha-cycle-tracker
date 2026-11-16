# Proposal

## Why

Prediction is the part of Cycle Tracker users act on, yet the code contradicts
the product's own decision record. BDR-0004 promises a prediction made of a
date plus an uncertainty window, an ovulation window, a fertile window, a real
confidence value, a late flag, and data warnings. The shipped code still returns
a bare date, hard-codes `prediction_confidence: 0.5`, falls back to the
configured cycle length when history is short, ignores outliers and gaps, and
derives phases from an arbitrary half-cycle offset. The `cycle-tracking` spec
still promises that old behavior, so no one implementing against it can know
which contract is real.

Prediction also has three competing sources of truth today — `coordinator.py`
builds cycle lengths and statistics, `sensor.py` recomputes ovulation from the
configured length, and `calendar.py` projects twelve future periods from the
configured length. They already disagree whenever history exists. The algorithm
has to become one pure function of history, reference date, and configuration
before the domain model, the card, or any new persistence backend can build on
it.

## What Changes

- Add a pure, framework-free prediction pipeline: stored periods → derived
  cycles → filtering → history window → strategy → `Prediction`.
- Introduce a new capability `cycle-prediction` that owns the pipeline
  contract, the output windows, confidence, warnings, phase derivation, and the
  projection of future cycle events.
- **BREAKING** Replace the prediction input rules: history is the last six
  completed cycles *after* filtering, filters apply before the window, cycles
  outside 15–90 days are excluded from prediction only, and the prediction
  window stops at the most recent gap longer than 90 days.
- **BREAKING** Remove the fallback to the configured cycle length. Below two
  usable completed cycles every prediction entity reports `unknown` and the
  pipeline returns no prediction.
- **BREAKING** Change what a prediction is: next period date plus uncertainty
  window (±1 population σ, never narrower than ±2 days), ovulation window
  (`next_period − 14` days, ±2 days), fertile window (five days before
  ovulation through ovulation day), confidence value and band, late flag, and
  data warnings.
- **BREAKING** Change the cycle-day and late contract: cycle day stops wrapping
  at the configured length, and days-until-period is reported as zero with an
  explicit late flag and late-day count, so a late period is distinguishable
  from a period due today.
- Add the median strategy alongside arithmetic mean and weighted moving average.
- Derive phases from the ovulation window instead of `cycle_length // 2`,
  with the configured period length taking priority when the windows overlap.
- Derive statistics from the same filtered six-cycle window as the prediction
  instead of all recorded cycles, and compute a real confidence value for the
  statistics sensor.
- Replace the calendar's twelve projected periods with events projected from the
  prediction, and add ovulation and fertile window events.
- Update the `cycle-tracking` spec so its requirements stop promising the
  removed fallback, the single ovulation date, and the constant confidence.

Out of scope for this change: Home Assistant event-bus events (`EVENT_*`
constants stay unused), the advanced outlier-bound override in the options
flow, late-period notifications, the Lovelace card, Google Sheets, and the
coordinator-to-use-case migration beyond the prediction seam.

## Capabilities

### New Capabilities

- `cycle-prediction`: turns recorded periods and a reference date into a
  prediction — filter rules, history window, strategy selection, uncertainty
  and fertility windows, confidence, late state, data warnings, phase
  derivation, and projection of future cycle events.

### Modified Capabilities

- `cycle-tracking`: next-period prediction loses the configured-length
  fallback; cycle phase and cycle day are derived from the prediction; ovulation
  becomes a window instead of a single date; statistics use the filtered
  six-cycle window and report a real confidence value.

## Impact

- `custom_components/cycle_tracker/prediction.py` gains strategies plus the
  pipeline; a framework-free domain module holds the value objects.
- `coordinator.py` becomes an adapter that supplies periods, configuration,
  and the reference date, and stops computing cycle lengths, statistics, and
  phases itself.
- `sensor.py`: seven entities change state and attribute contracts — `unknown`
  below minimum history, `days_until_period` no longer clamped, new window and
  warning attributes, confidence from the algorithm.
- `calendar.py`: predicted events come from the projection, and ovulation and
  fertile window entries are added.
- `const.py`: new attribute names and configuration keys for the median
  strategy; warning kinds.
- `openspec/specs/cycle-tracking/spec.md` is updated by this change's delta;
  `openspec/specs/cycle-prediction/spec.md` becomes a new main spec on archive.
- Tests: the project currently has no `tests/` directory. This change adds the
  first domain tests, which run without Home Assistant, and entity-level tests
  under the pinned Home Assistant baseline. Pre-commit gains the test hook and
  an import-boundary check for the domain module.
