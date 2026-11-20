# Tasks

## 1. Domain model and pure computation

- [x] 1.1 Add `FertilityState` string enum with the tokens `outside_estimated_fertile_window`, `within_estimated_fertile_window`, `unknown` and a frozen `FertilityEstimate` dataclass carrying state, base window, margin band, `margin_days`, `confidence`, `confidence_band` and `usable_cycle_count`; verify the model imports and a test asserts instances are immutable.
- [x] 1.2 Implement the pure `fertility_estimate(prediction, statistics, today)` function in `domain/fertility.py`: `margin = max(2, ceil(sigma))` from `CycleStatistics.cycle_length_std_dev`, base window unchanged, extended bands `[fertile_start - margin, ovulation_center + margin]` for the running and next cycles; verify unit tests cover σ=0 → margin 2, σ≈3.5 → margin 4, the 2026-11-15 centre producing 11-08→11-17, and a wider band for irregular cycles.
- [x] 1.3 Classify the reference date as `within` when inside either band, otherwise `outside`, and return `unknown` with no window or band when there is no prediction or fewer than two usable cycles; verify tests cover a date inside, a date between bands, one usable cycle, and that the configured cycle length is never used as a fallback.
- [x] 1.4 Guarantee determinism by passing the reference date in and never reading `date.today()`; verify a test returns identical estimates for identical inputs and shows the state changing with the reference date while the band for a given centre stays fixed.

## 2. Snapshot and configuration plumbing

- [x] 2.1 Add `CONF_ENABLE_FERTILITY_ESTIMATE` and `DEFAULT_ENABLE_FERTILITY_ESTIMATE = False` plus the new attribute constants in `const.py`, following the `enable_notifications` pattern; verify the constants import and a test asserts the default is `False`.
- [x] 2.2 Extend `Snapshot` with a `fertility` field and compute it unconditionally in `build_snapshot` from prediction, statistics and the reference date; verify a snapshot test shows the field populated for a two-cycle history and `unknown` below two cycles.
- [x] 2.3 Add `coordinator.get_enable_fertility_estimate()` through the existing `_setting` resolver; verify tests resolve options → data → `False` default for an entry without the key and return the enabled option value when set.
- [x] 2.4 Add the `enable_fertility_estimate` `BooleanSelector` to the options flow `init` schema beside `CONF_HISTORY_WINDOW`, defaulted via `_setting`, and leave `async_step_preferences` untouched; verify config-flow tests show it present in options, absent in initial setup, and that existing entries default to disabled, relying on the existing options-change reload.

## 3. Entity and translations

- [x] 3.1 Add `FertilityEstimateSensor` as a coordinator sensor with `translation_key = "fertility_estimate"`, the enum token as native state, and the base window, margin band, `margin_days`, `confidence`, `confidence_band` and `usable_cycle_count` as attributes; verify an entity test asserts the state tokens and all six attributes, and that no existing sensor gained a fertility attribute.
- [x] 3.2 Gate entity creation in `sensor.async_setup_entry` on `coordinator.get_enable_fertility_estimate()`; verify setup tests show no `fertility_estimate` entity when disabled and exactly one when enabled.
- [x] 3.3 Add `entity.sensor.fertility_estimate.state.*` labels and the options `enable_fertility_estimate` label to both `translations/en.json` and `pl.json`, using the exact PL labels „poza szacowanym oknem płodnym" / „w szacowanym oknie płodnym" / „brak danych"; verify both files parse as JSON and a test asserts the exact disclaimer from BDR-0004 is present verbatim and none of the banned words („bezpieczny", „dni bezpieczne", „możesz", „ryzyko zajścia") appear in the new copy.

## 4. Card presentation

- [x] 4.1 Add `fertility_estimate` to `DEFAULT_ENTITIES`, `CT_UNIQUE_SUFFIX` and `ENTITY_LABELS`, and add a conditional `_renderFertility()` on the render path that shows the factual label with the margin band beside it and the exact symmetric disclaimer, hidden when the entity is not tracked; verify a card test or DOM check shows no section when disabled, a populated section with the disclaimer when enabled, and the „brak danych" label for the unknown state.
- [x] 4.2 Turn the fertility section into a collapsed-by-default disclosure: heading as a `button` with `aria-expanded` and `aria-controls` pointing at the body, toggled by click and natively by Enter/Space, hiding the fact, band and disclaimer without deleting them, and storing no expanded state; verify `node --check custom_components/cycle_tracker/www/cycle-tracker-card.js`, a DOM smoke check for collapsed-by-default, expanded after activation and no section when the entity is absent, and the OpenDesign prototype updated to match.
- [x] 4.3 Move the fertility section after the statistics disclosure in the card template, so `<details class="fertility-section">` follows `<details class="stats-disclosure">` in the shadow-DOM markup; verify `node --check custom_components/cycle_tracker/www/cycle-tracker-card.js`, `grep -n` over the card showing the `stats-disclosure` line before the `fertility-section` line, `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7456/api/projects/c4c1e720-2026-4b11-9a20-c4c1e720ca2d/files/index.html` returning 200 with the fertility section after the statistics in the prototype, and no banned words („bezpieczny", „dni bezpieczne", „możesz", „ryzyko zajścia") in the moved copy.

## 5. Integration verification

- [x] 5.1 Run the full pytest suite and pre-commit hooks to confirm no regressions in `cycle-prediction` or config flows, and run `openspec validate "add-fertility-estimate" --type change` to confirm the planning artifacts are consistent; verify all pass with a clean git status showing only intended implementation files changed.
