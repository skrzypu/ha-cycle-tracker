# Proposal

## Why

The repository still carries a Kotlin Multiplatform (KMP) + FFI architecture that was abandoned: the code is pure Python, yet FFI contract schema, a contract validator, CI steps, pre-commit hooks, two KMP agents, and Gradle remnants remain. At the same time the component is not yet installable or updateable through HACS (custom repository), and it targets an obsolete Home Assistant baseline. Removing dead architecture and completing HACS integration packaging turns the project into a clean, publishable, portfolio-quality Python Home Assistant integration.

## What Changes

- **Remove all KMP/FFI remnants** — delete the FFI contract schema, contract validator script, CI contract step, pre-commit contract hook, KMP agent definitions, Gradle cache, FFI-shaped fixtures, and the KMP setup document; scrub KMP/FFI references from remaining agent definitions. **BREAKING** only for the now-removed contract-validation workflow (no runtime behavior change).
- **Target Home Assistant 2026.1.0** — set the minimum supported version in `manifest.json` and `hacs.json`, and bump dev/test dependencies to a HA 2026.1.0-compatible toolchain.
- **Make the integration HACS-ready as a custom repository** — move `hacs.json` to the repo root, fix the metadata to the real repository owner (`skrzypu`), add `iot_class`, add config-flow `strings.json` + `translations/en.json`, provide a portfolio-grade README, add `brand` assets, and add `hacs/action` + `hassfest` validation to CI. Distribute **only** as a HACS custom repository: never submit to `hacs/default`, so the integration is not listed or searchable in the HACS catalog.
- **Fix functional defects** — the "Days Until Ovulation" sensor calls a coordinator method that does not exist; services are never unregistered on config-entry unload; and next-period prediction uses a static configured cycle length instead of the average of recent cycle history.
- **Add test coverage** — config flow, sensors, calendar, and services, alongside the existing coordinator tests.

## Capabilities

### New Capabilities
- `cycle-tracking`: menstrual cycle domain behavior — period records, current cycle day and phase, next-period and ovulation prediction derived from recorded history, and cycle statistics.
- `cycle-logging-services`: the `log_start` / `log_end` services, local persistence of period data, and correct service registration/unregistration across the config-entry lifecycle.
- `hacs-distribution`: the integration's installability and metadata as a HACS custom repository — manifest requirements, HACS metadata location, config-flow UI strings/translations, brand assets, minimum HA version, and repository metadata.

### Modified Capabilities
<!-- None: openspec/specs is empty; all three capabilities are new. -->

## Impact

- **Removed files**: `specs/ffi-contract.schema.json`, `scripts/validate_contract.py`, `.opencode/agent/kmp-architect.md`, `.opencode/agent/kmp-implementer.md`, `TempFiles/opencode_setup_summary.md`, `tests/fixtures/sample_cycle_data.json`, `.gradle/`.
- **Modified files**: `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `.gitignore`, `custom_components/cycle_tracker/manifest.json`, `custom_components/cycle_tracker/coordinator.py`, `custom_components/cycle_tracker/sensor.py`, `custom_components/cycle_tracker/__init__.py`, `custom_components/cycle_tracker/services.py`, `.opencode/agent/api-researcher.md`, `.opencode/agent/code-explorer.md`, `.opencode/agent/test-engineer.md`, `TempFiles/product_roadmap_ha_cycle_tracker.md`.
- **New files**: root `hacs.json`, `custom_components/cycle_tracker/strings.json`, `custom_components/cycle_tracker/translations/en.json`, `brand/icon.png` (+ `@2x`), `.github/workflows/validate.yml`, README content.
- **Dependencies**: bump `pytest-homeassistant-custom-component` and related HA dev tooling to a HA 2026.1.0-compatible release.
- **Release**: create GitHub Release `v0.1.0` matching `manifest.json` version.
- **Distribution constraint**: repository remains public (HACS requirement) but is not submitted to `hacs/default`, so it does not appear in HACS search.
