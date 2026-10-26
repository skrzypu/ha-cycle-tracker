# Design

## Context

See `proposal.md` — Why. Current state that shapes the approach:

- The component under `custom_components/cycle_tracker/` is already pure Python (coordinator, sensor, calendar, config_flow, services), but the repository still carries a KMP/FFI toolchain: `specs/ffi-contract.schema.json`, `scripts/validate_contract.py`, a CI "Validate FFI Contract" step, a pre-commit `contract-validation` hook, `.opencode/agent/kmp-architect.md` / `kmp-implementer.md`, `.gradle/`, and an FFI-shaped fixture.
- `hacs.json` lives inside the component directory; the manifest and HACS metadata point at the wrong owner (`tomek` instead of `skrzypu`); `iot_class` is only in `hacs.json`, not the manifest; there is no `strings.json`, no `translations/`, no brand assets, and no `hacs/action`/`hassfest` CI.
- `.pre-commit-config.yaml` is gitignored, so the CI step `pre-commit run --all-files` cannot work on a clean checkout.
- Dev tooling pins HA 2025.1.4 (`pytest-homeassistant-custom-component 0.13.205`); the target is HA 2026.1.0.
- Functional defects: `sensor.py` calls `coordinator.get_next_ovulation_date()` which does not exist; `async_unload_entry` never unregisters services; next-period prediction uses the static configured cycle length rather than recorded history.
- The GitHub repository is public (required by HACS); there are no tags or releases.

## Goals / Non-Goals

**Goals:**

- Repository is Python-only with no KMP/FFI artifacts or references.
- The integration installs and updates through HACS as a custom repository, with valid manifest, HACS metadata, strings/translations, brand assets, and CI validation.
- Minimum supported Home Assistant version is 2026.1.0.
- Prediction is derived from recorded cycle history; the ovulation sensor and service lifecycle defects are fixed.
- Test coverage exists for the config flow, sensors, calendar, and services.

**Non-Goals:**

- Submitting to the HACS default catalog (explicitly excluded for privacy).
- Adding new product features beyond the roadmap Phase 1 scope (no Google Drive export, notifications wiring, Lovelace card, or extra biomarkers).
- Changing the local storage schema or migrating existing user data.
- Redesigning the config flow UX beyond supplying its required strings.

## Decisions

**1. Distribution: HACS custom repository only (public repo, no default-catalog PR).**
Chosen because the user wants portfolio visibility plus updates via HACS without appearing in HACS search. Alternatives rejected: default catalog (searchable — violates the privacy requirement) and private/no-HACS (HACS requires a public repo; would lose the portfolio and update path). Consequence: repository description and GitHub topics are still added (portfolio value); this improves GitHub discoverability but does **not** place the integration in the HACS catalog, which only a `hacs/default` pull request does.

**2. `hacs.json` at repository root with a minimal key set.**
`{ "name": "Cycle Tracker", "homeassistant": "2026.1.0", "render_readme": true }`. The current in-component file uses non-HACS keys (`category`, `iot_class`, `version`, `authors`, `keywords`, `repository`) and is deleted. Alternative considered: `zip_release` — rejected as unnecessary complexity for a small pure-Python integration.

**3. Manifest corrections.**
Keep `custom_components/cycle_tracker/manifest.json`; add `"iot_class": "local_polling"` (moved from `hacs.json`), set `documentation`/`issue_tracker` to `skrzypu/ha-cycle-tracker`, set `codeowners` to `["@skrzypu"]`, and set `"homeassistant": "2026.1.0"`. Keep `integration_type: "hub"` and `config_flow: true`. Domain already matches the directory name.

**4. Config-flow strings.**
Add `strings.json` (source of truth) and `translations/en.json` mirroring it, covering the `user`, `preferences`, and `notifications` steps plus their field labels and the selector translation keys (`prediction_algorithm`, `flow_intensity`). hassfest requires these to stay in sync, so they are maintained as a pair.

**5. Prediction algorithm via a strategy seam.**
Implement a small prediction module (`prediction.py`) with pure functions for arithmetic mean and weighted moving average over the most recent N (default 6) recorded cycle lengths, selected by the configured `prediction_algorithm`. The coordinator delegates to it and falls back to the configured cycle length when fewer than two completed cycles exist. This follows the project's OCP/SRP convention (strategies selectable without touching the coordinator) and keeps the existing `predict_next_period` contract. Alternatives rejected: inline branching in the coordinator (harder to test/extend), and a full class hierarchy (overkill for two algorithms).

**6. Move ovulation computation into the coordinator.**
Add `get_next_ovulation_date()` to the coordinator (the logic currently inlined in `sensor.py`), and have the sensor and `DaysUntilOvulationSensor` delegate to it. This fixes the missing-method defect and removes duplicated date math.

**7. Service lifecycle.**
Register `log_start`/`log_end` during `async_setup_entry` and register their removal with the entry's `async_on_unload`, so unloading the entry removes them and reloads do not leave duplicates. Alternative rejected: registering in `async_setup` once (no per-entry teardown and awkward multi-entry handling).

**8. CI: drop FFI, add HACS/hassfest validation.**
Remove the "Validate FFI Contract" step and the pre-commit `contract-validation` hook; commit `.pre-commit-config.yaml` (remove it from `.gitignore`). Add `.github/workflows/validate.yml` running `hacs/action` (`category: integration`) and `home-assistant/actions/hassfest@master`. Keep the existing pytest/ruff/mypy checks in `ci.yml`.

**9. Home Assistant 2026.1.0 toolchain.**
Pin `pytest-homeassistant-custom-component` to the release that ships HA 2026.1.0 and update `manifest.json`/`hacs.json` minimum versions accordingly. Run the suite against that baseline to surface any API drift between 2025.1 and 2026.1.

**10. Brand assets.**
Add `brand/icon.png` (256×256) and `brand/icon@2x.png` (512×512) at the repository root (the layout current HA/HACS expects). A designed asset is preferred; a compliant placeholder is acceptable since default-catalog submission is out of scope.

## Risks / Trade-offs

- **HA 2026.1 API drift breaks current code** → run the full test suite against the 2026.1.0 baseline before release; fix deprecations.
- **`hacs/action` fails on missing metadata** → add description, topics, issues-enabled, and brand assets so the action passes; a passing action does not list the repo in HACS.
- **`strings.json` and `translations/en.json` drift** → hassfest validation in CI catches desync.
- **Brand placeholder looks unpolished for a portfolio** → treat brand art as a design task; a placeholder is a deliberate fallback for the custom-repo phase.
- **Prediction behavior change alters `sensor.next_period_date` values** → covered by new unit tests and documented; storage schema is unchanged so no data migration is required.
- **Removing FFI tooling weakens "contract" assurance** → intentional; there is no FFI boundary, so the schema validated nothing. Existing pytest coverage becomes the contract.
- **Privacy vs portfolio tension** → description/topics help portfolio but increase GitHub discoverability; explicitly bounded by never submitting to `hacs/default`.

## Migration Plan

1. Land the change on `main` after CI (pytest + hacs/action + hassfest) passes.
2. Create GitHub Release `v0.1.0` matching `manifest.json`; set repository description and topics in GitHub settings.
3. Users install via HACS → Custom repositories → add the repo URL (category: Integration). No data migration — storage schema and key are unchanged.
4. Rollback: delete the release/tag and revert the commit; existing installs keep working from their current copy.

## Open Questions

- Exact `pytest-homeassistant-custom-component` version that pins HA 2026.1.0 (resolve during implementation; does not change approach).
- Whether to ship a designed brand icon or a compliant placeholder in the first release (deferrable; does not affect specs).
