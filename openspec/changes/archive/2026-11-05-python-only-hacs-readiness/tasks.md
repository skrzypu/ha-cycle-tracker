# Tasks

## 1. Remove KMP/FFI tooling (Python-only)

- [x] 1.1 Delete `specs/ffi-contract.schema.json` and `scripts/validate_contract.py`; verify with `git grep -i ffi` returning no matches in remaining tracked files
- [x] 1.2 Remove the "Validate FFI Contract" step from `.github/workflows/ci.yml`; verify `grep -i ffi .github/workflows/ci.yml` returns nothing
- [x] 1.3 Remove the `contract-validation` hook from `.pre-commit-config.yaml` and remove `.pre-commit-config.yaml` from `.gitignore`, then `git add .pre-commit-config.yaml`; verify `git ls-files --error-unmatch .pre-commit-config.yaml` succeeds
- [x] 1.4 Delete `.opencode/agent/kmp-architect.md` and `.opencode/agent/kmp-implementer.md`, and scrub KMP/Kotlin/FFI content from `api-researcher.md`, `code-explorer.md`, and `test-engineer.md`; verify `git grep -iE 'kmp|kotlin|ctypes|cbindgen' .opencode/agent` returns nothing
- [x] 1.5 Remove `.gradle/` and its `.gitignore` entry, delete `TempFiles/opencode_setup_summary.md`, remove or replace the FFI-shaped `tests/fixtures/sample_cycle_data.json`, and update `TempFiles/product_roadmap_ha_cycle_tracker.md` to a Python-only architecture (drop "Open Spec Kit" / `.spec.yaml` references); verify `git grep -iE 'kmp|kotlin|\bffi\b|gradle'` returns no matches outside `.venv`/vendor dirs
- [x] 1.6 Run `pytest tests/ -q` and `pre-commit run --all-files` and verify both pass after removals

## 2. Home Assistant 2026.1.0 baseline

- [x] 2.1 Pin `pytest-homeassistant-custom-component` (and related HA dev tooling) to the release that ships HA 2026.1.0; verify with `.venv/bin/pip show pytest-homeassistant-custom-component` and a version print of `homeassistant.const` — **DONE: `requirements-dev.txt` pins `pytest-homeassistant-custom-component==0.13.305` (which pins `homeassistant==2026.1.0`, requires Python >= 3.13); `.venv` rebuilt on CPython 3.13.13 and verified `homeassistant.const.__version__ == 2026.1.0`; CI moved to Python 3.13. The HA runtime itself lives on a separate server and is not needed for this pin.**
- [x] 2.2 Suite green on the HA 2026.1.0 baseline — **DONE at closure: `pytest tests/ -q` → 55 passed on CPython 3.13.13 / HA 2026.1.0, with drift confined to the test harness (`asyncio_mode = auto`, `frame.async_setup`), no production code changed. The suite was afterwards removed by project decision (see 5.7), so this evidence is historical; the pin and the baseline env remain in place for the roadmap.**

## 3. Prediction from history and ovulation fix

- [x] 3.1 Add a `prediction.py` module with arithmetic-mean and weighted-moving-average strategies plus configured-length fallback; verify unit tests cover mean, WMA (recent cycles weighted higher), and insufficient-history fallback
- [x] 3.2 Make the coordinator delegate `predict_next_period` to the prediction module and add `get_next_ovulation_date()`; verify unit tests assert history-based prediction and a non-null ovulation date
- [x] 3.3 Update `sensor.py` so `DaysUntilOvulationSensor` uses `coordinator.get_next_ovulation_date()`; verify a sensor unit test returns a non-negative integer and no `AttributeError`
- [x] 3.4 Add coordinator/statistics tests for the multiple-cycle case (currently skipped); verify the previously skipped `test_get_statistics_with_data` passes

## 4. Service lifecycle and behavior

- [x] 4.1 Register `log_start`/`log_end` in `async_setup_entry` and remove them via `entry.async_on_unload`; verify an unload test asserts both services are absent afterwards
- [x] 4.2 Add service tests for `log_start` (valid, same-day update, invalid flow intensity) and `log_end` (success, no open period); verify tests cover all specified scenarios

## 5. HACS distribution packaging

- [x] 5.1 Create root `hacs.json` with `{ name, homeassistant: "2026.1.0", render_readme: true }` and delete `custom_components/cycle_tracker/hacs.json`; verify `jq -e '.name' hacs.json` succeeds and no `hacs.json` exists under `custom_components/`
- [x] 5.2 Update `manifest.json`: add `iot_class: local_polling`, set documentation/issue_tracker to `skrzypu/ha-cycle-tracker`, codeowners `["@skrzypu"]`, and `homeassistant: 2026.1.0`; verify hassfest reports no manifest errors
- [x] 5.3 Add `strings.json` and `translations/en.json` covering the `user`, `preferences`, and `notifications` steps and the `prediction_algorithm`/`flow_intensity` selector keys; verify hassfest reports no strings mismatch
- [x] 5.4 Add `brand/icon.png` (256×256) and `brand/icon@2x.png` (512×512); verify dimensions with an image check (e.g. `file`/PIL)
- [x] 5.5 Write a portfolio-grade `README.md` with install (HACS custom repository) and usage instructions; verify the documented install steps match the shipped files
- [x] 5.6 Add `.github/workflows/validate.yml` running `hacs/action` (`category: integration`) and `home-assistant/actions/hassfest@master`; verify both jobs pass on a test push/PR
- [ ] 5.7 Add config-flow and calendar tests (steps, defaults, created entry; event range filtering); verify `pytest tests/ -q` covers them — **DEFERRED: the whole test suite (`tests/`, `pytest.ini`, the `python-tests` pre-commit hook and the CI test step) was removed by project decision on 2026-11-05 because the project is still at skeleton stage and tests encoded behaviour the specs do not yet define. Tests will be reintroduced from the roadmap specifications; the earlier calendar/config-flow drafts are kept outside the repo in `/tmp/opencode/cycle-tracker-wip/` and the deleted unit suite is preserved in git history (commit 69cb34d).**

## 6. Release and repository metadata

- [ ] 6.1 Create and push git tag `v0.1.0` and a matching GitHub Release; verify `gh release view v0.1.0` and that the tag matches `manifest.json` version — **BLOCKED: needs explicit permission to push/tag**
- [ ] 6.2 Set the GitHub repository description and topics in settings; verify with `gh repo view --json description,repositoryTopics` — **BLOCKED: needs explicit permission**
- [x] 6.3 Confirm no pull request to the HACS default catalog is opened and the integration is custom-repository-only; verify no `hacs/default` PR exists and HACS custom install works by URL — **DONE (non-submission verified 2026-11-05): `gh pr list --repo hacs/default --author skrzypu --state all` returns nothing, `skrzypu/ha-cycle-tracker` is absent from the `hacs/default` integration list, and the only HACS reference in this repository is the `hacs/action` validator inside our own CI, which lints metadata and submits nothing. Catalog inclusion requires a manual maintainer-reviewed PR, which has not been opened and must not be. The custom-install-by-URL check is a manual step on the Home Assistant host and cannot be verified from this environment.**
