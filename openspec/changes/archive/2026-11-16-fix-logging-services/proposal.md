# Proposal

## Why

Both logging services are unusable on the supported Home Assistant 2026.1
baseline: `handle_log_start` and `handle_log_end` read `call.config_entry`, an
attribute `ServiceCall` does not have (`__slots__` is `context`, `data`,
`domain`, `hass`, `return_response`, `service`), so every call raises
`AttributeError`. Independently, a call that carries a `target` fails schema
validation, because `ServiceRegistry.async_call` merges the target into the
service data before validating and both schemas reject unknown keys. The only
documented way to log a period therefore cannot work, which means the
prediction added by `add-cycle-prediction` has no data to work with in a real
installation.

## What Changes

- Resolve the target config entry from the call's target (entity, device or
  area) through the entity registry, falling back to the single configured
  entry when no target is given. Reject a foreign target or an ambiguous setup
  with a validation error and leave stored data untouched.
- Accept `entity_id`, `device_id` and `area_id` in both service schemas so a
  call made with a target passes validation.
- Publish a target selector in `services.yaml` for the integration's entities.
- Reject `log_end` with a date before the period start instead of storing an
  inverted range that the adapter then has to discard.
- Add adapter tests that drive the real service registry with
  `hass.services.async_call(..., target=...)`.
- No change to the persisted data format or to the response shape
  (`success`/`message`) of either service.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cycle-logging-services`: service invocation contract — how a call resolves
  its config entry, which targets are accepted, what happens on an invalid or
  ambiguous target, and the fact that a started period stays open until
  `log_end`.

## Impact

- `custom_components/cycle_tracker/services.py`, `services.yaml`
- `tests/adapters/test_services.py` (replaces the coordinator-only proxy tests
  with service-registry calls)
- No change to `coordinator.py`, the store, `STORAGE_VERSION` or the domain
  package.
