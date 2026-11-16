# Design

## Context

Three defects share one root area: the integration treats the config entry as a
first-run seed and then forgets it. Settings are copied into the store, the
options flow cannot even open, and the coordinator is not tied to the entry's
lifecycle. The blind mypy hook is why none of this was caught: without
`homeassistant` installed, `OptionsFlow.config_entry` is `Any` and a read-only
assignment looks fine.

## Decisions

### 1. The config entry owns settings; the store owns periods

`CoordinatorConfig`-style values are resolved on every read:

```python
def _setting(self, key: str, default: T) -> T:
    return self.entry.options.get(key, self.entry.data.get(key, default))
```

`_get_default_data()` reduces to `{"periods": []}`, and `_async_update_data()`
normalizes whatever the store holds into `{"periods": [...]}`. Settings keys
already present in stored data are dropped from memory and disappear on the next
save; they were only ever a copy of `entry.data`, so nothing is lost. Getters
(`get_cycle_length`, `get_period_length`, `get_prediction_algorithm`,
`get_last_period_start` and the notification getters) call `_setting`.

Why not `OptionsFlowWithReload`? It is the modern replacement for the
update-listener reload pattern, but switching would also change how the entry
reloads on option changes, which is outside this fix. The existing
`entry.add_update_listener(async_reload_entry)` already reloads after the
options flow writes, so the settings are re-read on the next setup.

### 2. The options flow takes no constructor argument

`OptionsFlow.config_entry` is a read-only property computed from the flow's
`handler` and `hass`; it raises inside `__init__` because `hass` is not set yet.
`ConfigFlow.async_get_options_flow` is a `@staticmethod`, so the correct shape is:

```python
@staticmethod
@callback
def async_get_options_flow(config_entry: ConfigEntry) -> CycleTrackerOptionsFlow:
    return CycleTrackerOptionsFlow()
```

The `config_entry` parameter stays for the protocol; the flow reads
`self.config_entry` inside `async_step_init`, where it is populated. Defaults use
the same resolution order as the coordinator (`options` → `data` → default), so
reopening the dialog shows the values in force instead of the original setup
values.

### 3. `ConfigFlowResult` instead of `FlowResult`

`homeassistant.data_entry_flow.FlowResult` is the legacy alias;
`homeassistant.config_entries.ConfigFlowResult` is the typed current name. All
step signatures and `async_get_options_flow` are annotated with it, including the
options flow's `async_step_init`.

### 4. Explicit shutdown on unload

`async_unload_entry` pops the coordinator and calls `await coordinator.async_shutdown()`
before returning. Passing `config_entry` to `DataUpdateCoordinator.__init__` would
make Home Assistant register the shutdown automatically, but that also changes
construction for every test and hides the cleanup behind framework behaviour; an
explicit call is one line, testable, and independent of the base class. Both are
idempotent, so this remains safe if the coordinator is later constructed with a
config entry.

### 5. mypy runs where `homeassistant` is installed

The hook becomes a local `language: system` hook, like the existing pytest hook,
so it uses the project environment created from `requirements-dev.txt`
(`homeassistant==2026.1.0` is pinned through
`pytest-homeassistant-custom-component`). CI already installs those requirements
before running pre-commit. The hook is scoped to `^custom_components/` so the
gate covers production code — test modules are checked by pytest and would
otherwise force annotations on every fixture.

`--ignore-missing-imports` stays for genuinely untyped third-party modules, but
`--disable-error-code=call-arg` and `--disable-error-code=var-annotated` — which
only existed to paper over `Any` — are removed if the tree is clean without them.
`--explicit-package-bases` stays, because `custom_components` is not an installed
package root.

## Risks

- **Self-hosted CI with no dev environment**: a `language: system` hook needs the
  requirements installed first. The CI workflow already does that for the pytest
  hook, so the mypy hook inherits the same precondition; a contributor running
  pre-commit without the venv gets a clear "mypy: command not found" instead of a
  silently blind gate.
- **Stale stored settings**: normalized away on load. If a user downgrades, the
  old code re-seeds from `entry.data`, which is what the values came from.
- **Options flow defaults** now read `options` first; a value saved once is shown
  again, but `entry.data` is never rewritten, so removing an option is not
  possible from the dialog. Out of scope.

## Migration

None required. Existing entries keep their `data`; existing stores keep their
periods and lose only duplicated settings keys.
