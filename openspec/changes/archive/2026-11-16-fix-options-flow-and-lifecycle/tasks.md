# Tasks

## 1. Options flow

- [x] 1.1 Remove `__init__` from `CycleTrackerOptionsFlow`, construct it with no arguments from `async_get_options_flow`, and keep the `config_entry` parameter on the static method for the protocol
- [x] 1.2 Annotate every flow step and `async_get_options_flow` with `ConfigFlowResult`, replacing the deprecated `FlowResult`
- [x] 1.3 Pre-fill the options form defaults from `entry.options` → `entry.data` → built-in default

## 2. Settings source

- [x] 2.1 Add a single setting resolver on the coordinator (`options` → `data` → default) and route every configuration getter through it
- [x] 2.2 Reduce the default data to recorded periods and normalize whatever the store holds to `{"periods": [...]}` on load, so stored setting copies stop overriding the config entry

## 3. Unload

- [x] 3.1 Shut the coordinator down in `async_unload_entry` after removing it from the integration's runtime data

## 4. Tests

- [x] 4.1 Open the options flow through `hass.config_entries.options.async_init` and assert a form with the current values is returned instead of an error
- [x] 4.2 Submit a changed cycle length and assert the entry options are updated and the reloaded coordinator reports the new value
- [x] 4.3 Assert a stored setting copy does not override the config entry
- [x] 4.4 Assert unloading the entry shuts the coordinator down and clears the runtime data

## 5. Type gate

- [x] 5.1 Replace the isolated mypy hook with a local hook that runs in the project environment, scoped to `custom_components/`
- [x] 5.2 Remove the `call-arg` and `var-annotated` suppressions if the tree is clean without them, keeping `--ignore-missing-imports` and `--explicit-package-bases`
- [x] 5.3 `pre-commit run --all-files` passes with the hook seeing real Home Assistant types

## 6. Verification

- [x] 6.1 `pytest -q` passes
- [x] 6.2 `openspec validate fix-options-flow-and-lifecycle --strict` reports valid
