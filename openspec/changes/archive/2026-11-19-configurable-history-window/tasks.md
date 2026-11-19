# Tasks

## 1. Setting, defaults and resolver wiring

- [x] 1.1 Add `CONF_HISTORY_WINDOW`, `MIN_HISTORY_WINDOW = 6`, `MAX_HISTORY_WINDOW = 24`, `DEFAULT_HISTORY_WINDOW_NEW_ENTRY = 12` and `ATTR_LIFETIME_AVERAGE_CYCLE_LENGTH = "lifetime_average_cycle_length"` to `custom_components/cycle_tracker/const.py`, leaving `domain.ports.DEFAULT_HISTORY_WINDOW = 6` as the fallback; verify the constants import and existing tests still pass under pytest.
- [x] 1.2 Add `get_history_window()` to `coordinator.py` using `_setting(CONF_HISTORY_WINDOW, DEFAULT_HISTORY_WINDOW)` and pass `history_window=self.get_history_window()` in `get_prediction_config()`; verify with `tests/adapters/test_coordinator_snapshot.py` (or a new coordinator test) that options override data, data overrides the 6 fallback, and the resulting `PredictionConfig` carries the chosen window.
- [x] 1.3 Add a `NumberSelector` (min 6, max 24, step 1) to the setup preferences step with default 12 and to the options flow with a resolver-based default; verify in `tests/adapters/test_config_flow.py` / `test_config_flow_sheet.py` that a new entry stores 12 in `entry.data`, an existing entry with no value still resolves to 6, an option overrides both, and 5/25 are rejected.
- [x] 1.4 Add the `history_window` label/help to `config.step.preferences.data`, `options.step.init.data` in `strings.json`, `translations/en.json` and `translations/pl.json`; verify `tests/adapters/test_translations.py` passes and no new service for the window is registered.

## 2. Generalize the existing window and confidence behavior

- [x] 2.1 Replace "six"/`n/6` wording with N/`n/N` in the docstrings of `domain/ports.py`, `domain/history.py`, `domain/statistics.py` and `domain/prediction.py` without changing the selection or confidence code; verify a grep finds no stale six-cycle wording in those modules and `tests/domain/` still passes.
- [x] 2.2 Add domain tests covering that one `config.history_window` drives both the usable window and the confidence denominator (N=6 vs N=12, same six stable cycles scoring about 0.96 vs about 0.48) in `tests/domain/test_history.py`, `test_statistics.py` and `test_prediction.py`; verify pytest passes and the two-cycle minimum, filter-before-window and gap-truncation scenarios stay green.

## 3. Lifetime cycle-length average

- [x] 3.1 Extend the frozen `History` dataclass in `domain/history.py` with `in_range` (default empty), populated in `build_history()` using the same `_within_bounds()` predicate but without gap truncation or the N slice; verify tests in `tests/domain/test_history.py` show outliers excluded, pre-gap cycles retained in `in_range`, and `usable` unchanged.
- [x] 3.2 Add `lifetime_average_cycle_length` to `CycleStatistics` in `domain/statistics.py`, computed with `fmean` over `history.in_range` and `None` when it is empty, leaving the windowed average intact; verify tests in `tests/domain/test_statistics.py` cover 28/10/30 yielding 29, the pre-gap case, empty history yielding unknown, and existing statistics scenarios.
- [x] 3.3 Expose the new value through `ATTR_LIFETIME_AVERAGE_CYCLE_LENGTH` in `CycleStatisticsSensor.extra_state_attributes` in `sensor.py`; verify `tests/adapters/test_sensors.py` asserts the attribute is present with the computed value and is `None` when no in-range cycle exists.

## 4. Card presentation and strings

- [x] 4.1 Add the windowed and lifetime averages as two labelled rows in the existing `rows` array of `_renderStatistics` in `custom_components/cycle_tracker/www/cycle-tracker-card.js`, reusing `formatNumeric(..., 1)` and the not-tracked path; verify by manual browser checklist that both Polish-labelled rows render and that a missing lifetime value shows "brak danych" while the windowed row still renders (no JS test harness exists).
- [x] 4.2 Verify the card asset is still served at its versioned URL via `tests/adapters/test_static_path.py`, and that no second card element or dashboard seed is introduced.

## 5. Downstream artifacts to align (do not edit during planning)

- [x] 5.1 Update the requirements "Select the last six usable completed cycles", "Report prediction confidence" and "Exclude out-of-range cycles from prediction" in `openspec/specs/cycle-prediction/spec.md` to the N window, `n/N` and exclusion wording; verify the main spec matches the `cycle-prediction` delta and contains no literal six-cycle or `n/6` rule.
- [x] 5.2 Update `openspec/specs/cycle-configuration/spec.md` with the shared 6–24 window setting, its two defaults and the options-only rule; verify it matches the `cycle-configuration` delta.
- [x] 5.3 Update the statistics sensor requirement in `openspec/specs/cycle-tracking/spec.md` for the N window and add the lifetime average; verify it matches the `cycle-tracking` delta.
- [x] 5.4 Update the collapsible statistics requirement in `openspec/specs/lovelace-card/spec.md` for the two labelled averages; verify it matches the `lovelace-card` delta.
- [x] 5.5 Update `docs/guide/algorithms.md` to describe the configurable N window, `min(1, 1−σ/mean) × min(1, n/N)`, outlier exclusion from both averages, and the lifetime average; verify no stale "six"/`n/6` wording remains.
- [x] 5.6 Confirm no **new** edits to `docs/bdr/0004-prediction-is-a-window-not-a-date.md` or `docs/ideas/prediction-configurability.md` during this change. Both already carry the intended 2026-11-19 decision record (BDR amendment, I-013 `decided`) and are modified relative to HEAD from that prior step, so "no git diff" cannot be the criterion. Verify their content still matches the pre-implementation baseline — SHA-256 `2542cf60e77691a1e7a4189e90de05bfbfba524d41b9034e28edb1fb97f7ceed` and `af04466aa171146b8c6381a1d910c87688f3b59752019d92a90e7c8ebabc1788` — and that no other BDR or idea file was touched.

## 6. Verification gate (integration check only)

- [x] 6.1 Run `pre-commit run --all-files` (ruff, ruff-format, mypy, pytest) and verify exit code 0 with no changed files left unformatted.
- [x] 6.2 Exercise the full flow once end to end with a fresh entry (window 12) and an existing entry (window 6), then save an option of 18 and confirm prediction, confidence and both averages update after reload; verify the observed sensor attributes and card rows.
