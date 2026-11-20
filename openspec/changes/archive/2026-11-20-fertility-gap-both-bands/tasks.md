# Tasks

## 1. Domain model and gap edges

- [x] 1.1 Add `previous_margin_band` and `next_margin_band` fields (`tuple[date, date] | None`) to the frozen `FertilityEstimate` in `domain/fertility.py`; verify the model imports and a test asserts instances remain immutable and that both fields default to `None` where constructed.
- [x] 1.2 Derive both edges inside the existing `fertility_estimate()` from the bands it already builds: previous only when `current_band[1] < today`, next only when `next_band[0] > today`, and both `None` in the `within` and `unknown` states; verify unit tests cover a reference date between two bands (2026-11-20, centres 11-15 and 12-13, margin 2 → 11-08..11-17 and 12-06..12-15), a date before the only band (no previous edge), an `unknown` estimate (no edges), and that no extra cycle is projected.
- [x] 1.3 Keep the pure signature `(prediction, statistics, today)` with no clock read or persistence, and leave the state token, base window, `margin_band`, margin, confidence fields and usable-cycle count unchanged; verify a test compares full estimates before/after for a `within` and an `unknown` case and asserts identical inputs produce identical edges.

## 2. Entity attributes

- [x] 2.1 Add `ATTR_PREVIOUS_MARGIN_BAND` and `ATTR_NEXT_MARGIN_BAND` to `const.py` and expose them from `FertilityEstimateSensor.extra_state_attributes` in `sensor.py` using the existing `_iso_window()` helper, as ISO pairs or `None`; verify an entity test checks both attributes in an `outside` case with two edges, a `null` previous edge when only the next exists, and that existing attributes and their values are unchanged.
- [x] 2.2 Run the domain and entity test files added in this change and confirm they pass before moving to presentation; record the exact command and result in the report.

## 3. Card and prototype presentation

- [x] 3.1 Add two factual labels („poprzedni pas szacunku", „następny pas szacunku") to `FERTILITY_TEXT` in `www/cycle-tracker-card.js` and make `_renderFertility()` render one labelled line per available edge in the `outside` state using `_formatFertilityBand()`, with no line for an absent edge; verify `node --check` passes, a DOM check shows two lines with both edges, one line with only the next edge, no band line for `unknown`, unchanged `within` rendering, the verbatim BDR-0004 disclaimer, and no occurrence of „bezpieczny", „dni bezpieczne", „możesz" or „ryzyko zajścia".
- [x] 3.2 Update `/tmp/opencode/cycle-tracker-fertility-prototype-light.html` and `-dark.html` (and their shared `styles.css` if needed) to show the labelled both-edge `outside` variant plus the one-edge variant, then copy them into the existing `open-design` container project `/app/.od/projects/c4c1e720-2026-4b11-9a20-c4c1e720ca2d/` as `index.html` and `dark.html` with `docker cp`; verify both preview URLs under `http://127.0.0.1:7456/api/projects/c4c1e720-2026-4b11-9a20-c4c1e720ca2d/files/` return HTTP 200 and serve the new labels, and that no new files appear in the repository.

## 4. Release and integration verification

- [x] 4.1 Bump the patch version `0.2.6` → `0.2.7` in `custom_components/cycle_tracker/manifest.json` and the `?v=` example in `README.md`, per ADR-0016; verify no `0.2.6` remains in those two files and that the runtime card URL derives its version from the manifest.
- [x] 4.2 Run the full pytest suite, `pre-commit run --all-files` and `openspec validate "fertility-gap-both-bands" --type change --strict`; verify all pass and the git status shows only the intended implementation, test, documentation and version files.
- [x] 4.3 After the change is archived, rebuild the distribution with `python3 .opencode/skills/ha-package/scripts/build.py`; verify the 0.2.7 zip and tar.gz contain the updated card and domain module, all members match the sources byte-for-byte, and record both SHA-256 values in the report.

## 5. Days since the previous band

- [x] 5.1 Add `previous_band_days_ago: int | None` to the frozen `FertilityEstimate` and compute it in the `outside` branch as `(today - current_band[1]).days` only when the previous edge exists; keep it `None` in `within`, `unknown` and whenever the previous edge is absent; verify unit tests cover 2026-11-17 → 2026-11-20 giving 3 days, no previous edge giving `None`, and unchanged `within`/`unknown` payloads.
- [x] 5.2 Add `ATTR_PREVIOUS_BAND_DAYS_AGO` to `const.py` and expose it from `FertilityEstimateSensor.extra_state_attributes` as an integer or `None`; verify an entity test checks 3 for a previous edge ending 2026-11-17 with today 2026-11-20, `None` when the edge is absent, and that all eight earlier attributes keep their values.
- [x] 5.3 Append „zakończył się N dni temu" to the previous-edge line in `_renderFertility()` in `www/cycle-tracker-card.js`, using the new attribute only when it is a number, and update both OpenDesign prototypes and their copies in the `open-design` container; verify `node --check`, DOM smoke-check for the suffix present, absent when the attribute is missing, and no occurrence of „bezpieczny", „dni bezpieczne", „możesz" or „ryzyko zajścia".
- [x] 5.4 Run the full pytest suite, `pre-commit run --all-files` and `openspec validate "fertility-gap-both-bands" --type change --strict`; verify all pass, then rebuild the 0.2.7 distribution with the ha-package skill and record both SHA-256 values. No version bump: this work extends the same unarchived change.

## 6. Card scenario coverage

- [x] 6.1 Add an automated static test of `custom_components/cycle_tracker/www/cycle-tracker-card.js` covering the three card scenarios in the delta spec that lacked tests: „Two labelled edges", „One labelled edge" and „Copy stays factual". Assert that both factual labels („poprzedni pas szacunku", „następny pas szacunku") are present, that `_renderFertility()` reads `previous_margin_band` and `next_margin_band`, that an absent edge produces no line, and that the verbatim BDR-0004 disclaimer is present while none of „bezpieczny", „dni bezpieczne", „możesz" or „ryzyko zajścia" appears in the new copy; verify with pytest, ruff and ruff-format.
