# Tasks

## 1. Test infrastructure

- [x] 1.1 Add pytest configuration (`pyproject.toml` or `pytest.ini`) with `asyncio_mode = auto` and `testpaths = tests`; verify `pytest --collect-only` exits 0
- [x] 1.2 Create `tests/domain`, `tests/adapters` and `tests/imports`; verify pytest collects them and reports no errors
- [x] 1.3 Add an AST import-boundary test that fails when any module under `custom_components/cycle_tracker/domain/` imports Home Assistant, `aiohttp` or `voluptuous`; verify it passes now and fails against a temporary violating import
- [x] 1.4 Add a pytest hook to `.pre-commit-config.yaml`; verify `pre-commit run pytest --all-files` runs and passes

## 2. Domain models and ports

- [x] 2.1 Add `domain/models.py` with frozen `Period`, `Cycle`, `Prediction`, `DataWarning`, `ConfidenceBand` and `CyclePhase`; verify a unit test constructs each and the import-boundary test still passes
- [x] 2.2 Add `domain/ports.py` with a `Clock` protocol and `PredictionConfig`; verify a unit test injects a fixed clock and mypy accepts the protocol
- [x] 2.3 Add a helper that derives a stable period id (`uuid5` over the start date) for legacy rows; verify a test yields the same id across two calls for the same start date

## 3. History derivation

- [x] 3.1 Add `domain/history.py` deriving cycle lengths from consecutive period starts, oldest first, ignoring open periods; verify tests for three starts producing two lengths and for an open period producing none
- [x] 3.2 Filter cycles outside the configured bounds and emit `outlier` warnings naming the offending period; verify tests for a 120-day and a 10-day cycle, including that they stay out of the usable set
- [x] 3.3 Stop the usable history at the most recent gap longer than 90 days and emit a `gap` warning for the boundary period; verify tests for a 187-day gap and for recovery needing two new cycles
- [x] 3.4 Select at most the six most recent usable cycles after filtering; verify tests for eight usable lengths and for a shorter window
- [x] 3.5 Return usable cycles and warnings from one function so prediction and statistics share them; verify `predict()` and `statistics()` receive the same object in a test

## 4. Prediction strategies

- [x] 4.1 Add a shared `round_half_up()` helper; verify tests for 28.5 to 29 and 27.5 to 28
- [x] 4.2 Implement arithmetic mean, weighted moving average and median strategies; verify tests for 26/30/31, 26/30 and 26/30/31/27 resolving to 29 days
- [x] 4.3 Add a strategy registry keyed by configuration name with the weighted moving average as default, logging a warning on an unknown name; verify a test for the three names and for the unknown fallback

## 5. Prediction pipeline

- [x] 5.1 Add `domain/prediction.py` with `predict()` returning `None` below two usable cycles; verify tests for the next period date and for the no-fallback case
- [x] 5.2 Compute the uncertainty window from population standard deviation, rounding σ up and flooring the half-width at two days; verify tests for 28/28 giving ±2 days and for 25/32/26/33 giving ±4 days
- [x] 5.3 Compute the ovulation window and the fertile window from the predicted next period, clamped to the cycle start; verify tests for 2026-12-01 giving 2026-11-15 to 2026-11-19 and 2026-11-12 to 2026-11-17
- [x] 5.4 Compute confidence and band from the usable set; verify tests for 0.33 low, 0.59 medium and 0.96 high
- [x] 5.5 Compute the late flag, late-day count and clamped days-until-period; verify tests for three days remaining, four days late and a late period cleared by a new start

## 6. Cycle phases

- [x] 6.1 Add phase derivation that uses the actual next start for completed cycles and the predicted next period for the current cycle; verify the 28-day/5-day boundary test: menstrual 1-5, follicular 6-12, ovulatory 13-17, luteal 18-28
- [x] 6.2 Apply the configured period length first, clipping the ovulatory window and dropping the follicular phase when it disappears; verify the 21-day/7-day test yielding menstrual 1-7, ovulatory 8-10, luteal 11-21
- [x] 6.3 Return no phase when no prediction exists; verify the test with fewer than two usable cycles

## 7. Event projection

- [x] 7.1 Add `domain/events.py` projecting 12 cycles forward by the predicted length, emitting period, ovulation and fertile events per cycle; verify the test where 2026-12-01 plus 30 days yields 2026-12-31
- [x] 7.2 Project from the predicted date even when it is in the past, so a late period does not shift the calendar silently; verify a test with a late prediction

## 8. Statistics

- [x] 8.1 Add `domain/statistics.py` using the shared usable window for cycle statistics and completed periods for period statistics; verify tests for a single cycle, multiple cycles and an open period
- [x] 8.2 Report `total_cycles_tracked` as the number of recorded periods and include confidence and band when a prediction exists; verify tests for one period and for an open period

## 9. Home Assistant adapters

- [x] 9.1 Implement `Clock` with `dt_util.now().date()` and cache the derived snapshot keyed by the local date in the coordinator; verify a test that a date change recomputes and the same date does not
- [x] 9.2 Adapt stored period dictionaries to `Period` at the coordinator boundary without changing the storage format; verify a test loading legacy rows produces usable cycles and stable ids
- [x] 9.3 Switch the seven sensors to the snapshot, reporting `unknown` without a prediction and exposing the window, warning, late and confidence attributes; verify adapter tests for the fresh-install and no-prediction states
- [x] 9.4 Replace the wrapping cycle-day calculation with the elapsed-day count; verify the test where 33 elapsed days report cycle day 34
- [x] 9.5 Replace the calendar's configured-length projection with projected domain events and add ovulation and fertile entries; verify `async_get_events` returns recorded, predicted, ovulation and fertile events for a range
- [x] 9.6 Remove the duplicated phase, ovulation and statistics arithmetic from `coordinator.py` and the root `prediction.py`, leaving one implementation; verify `grep` finds no half-cycle or `prediction_confidence: 0.5` arithmetic left
- [x] 9.7 Update the README entity table and `docs/guide/algorithms.md` where the shipped contract changed (unknown states, late attributes, median, windowed statistics); verify every documented value matches an assertion in the tests

## 10. Integration verification

- [x] 10.1 Run `pre-commit run --all-files` and verify ruff, mypy and pytest pass
- [x] 10.2 Run `openspec validate add-cycle-prediction --strict` and verify it passes
- [x] 10.3 Run the full test suite and verify the domain import-boundary test, domain tests and adapter tests all pass together
