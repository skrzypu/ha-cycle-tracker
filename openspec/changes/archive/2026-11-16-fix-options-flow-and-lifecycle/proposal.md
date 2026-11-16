# Proposal

## Why

On the Home Assistant 2026.1 baseline the options dialog cannot be opened and,
even if it could, saving it would change nothing:

- `CycleTrackerOptionsFlow.__init__` assigns `self.config_entry`, but
  `OptionsFlow.config_entry` is a read-only property derived from the flow
  handler, so assigning it raises `AttributeError` and the flow never starts.
  The flow also annotates its steps with the deprecated `FlowResult`.
- The coordinator takes its settings from the store, which is seeded from
  `entry.data` only on the very first load; afterwards the stored copy wins
  forever. The options flow writes `entry.options`, which nothing reads, so
  changing cycle length, period length or the prediction algorithm has no
  effect on any entity.
- `async_unload_entry` drops the coordinator without shutting it down. Home
  Assistant only auto-registers `async_shutdown` for coordinators constructed
  with a config entry, and this one is not, so the refresh timer and the
  debouncer outlive the unload.
- The mypy hook runs in an isolated environment without `homeassistant`, so
  `--ignore-missing-imports` turns every Home Assistant type into `Any`. It
  reported the three defects above as clean, which is why they survived.

## What Changes

- Remove the options-flow `__init__`, construct the flow with no arguments from
  `async_get_options_flow`, and annotate every flow step with `ConfigFlowResult`.
- Show current effective values in the options form (`options` → `data` →
  default) so the dialog reflects what the integration actually uses.
- Resolve every setting from the config entry at read time (`options` → `data` →
  default). The store keeps recorded periods only, and settings left in existing
  stored data are ignored rather than deleted by force.
- Shut the coordinator down in `async_unload_entry`.
- Point the mypy hook at the project environment, where `homeassistant` is
  installed, and scope it to the integration package so the gate sees real types.
- Add tests for the options flow round trip, for settings reaching the
  coordinator after an options change, and for the shutdown on unload.

## Capabilities

### New Capabilities

- `cycle-configuration`: how a user changes cycle length, period length,
  prediction algorithm and notification preferences after setup, and how the
  integration resolves and applies those settings.
- `integration-lifecycle`: what the integration must release when its config
  entry is unloaded.

### Modified Capabilities

None.

## Impact

- `custom_components/cycle_tracker/config_flow.py`, `coordinator.py`,
  `__init__.py`
- `.pre-commit-config.yaml` (mypy hook environment and scope)
- New `tests/adapters/test_config_flow.py` and `tests/adapters/test_lifecycle.py`
- No change to `STORAGE_VERSION`; existing stored data keeps working.
