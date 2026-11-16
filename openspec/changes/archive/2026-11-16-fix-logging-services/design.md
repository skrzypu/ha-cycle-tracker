# Design

## Context

`services.py` was written against an imagined `ServiceCall` API: it reads
`call.config_entry.entry_id` to find its coordinator. Home Assistant 2026.1 has
no such attribute, so the handlers fail before touching data. The schemas also
reject the target keys that `ServiceRegistry.async_call` injects into the
service data, so even a correct handler would not be reached when a call is
made with a target. The deleted skeleton test suite missed both problems
because its fixture built a fake call object with an invented `config_entry`
attribute.

## Goals / Non-Goals

**Goals**

- A service call works from the UI, from YAML with no target, and from YAML
  with an entity/device/area target.
- A wrong or ambiguous target produces an actionable error instead of mutating
  data.
- Tests exercise the registered service, not a hand-built stand-in.

**Non-Goals**

- Changing how periods are stored, or persisting a `period_id`.
- Registering services per config entry. They stay domain-level and are removed
  on unload, as `cycle-logging-services` already requires.
- Notifications or scheduling.

## Decisions

### 1. Resolution reads the registry, not the call object

`async_extract_entity_ids(call)` expands `entity_id`, `device_id` and `area_id`
from the call data (`TargetSelection` handles all three). Each extracted entity
id is looked up in the entity registry to obtain its `config_entry_id`; the
resulting entry ids are deduplicated.

- Exactly one entry id → that coordinator.
- More than one → `ServiceValidationError`: the target spans several entries.
- Target given but no entity belongs to this integration → `ServiceValidationError`.
- No target → the only coordinator in `hass.data[DOMAIN]`; with zero or several
  coordinators, a `ServiceValidationError` explains that the call must target an
  entity of the integration.

This relies only on public structures (`hass.data`, the entity registry) and
keeps the handler signature unchanged.

### 2. Target keys are part of both schemas

`ServiceRegistry.async_call` does `service_data.update(target)` before the
schema runs and `vol.Schema` defaults to `extra=PREVENT_EXTRA`. Both schemas
therefore accept optional `entity_id`, `device_id` and `area_id`. The values are
not used by the handlers directly; resolution goes through
`async_extract_entity_ids`, so group entities and area/device targets expand the
same way they do in core integrations.

### 3. An open period is the encoded `end_date == start_date` row

`log_start` writes `end_date = start_date` and `log_end` requires that equality
before it will close the period. The domain adapter now maps that row to
`end=None` (`add-cycle-prediction`), so period statistics ignore it and the
logging contract stays backwards compatible with data already on disk. The
delta spec records this behaviour instead of leaving it implicit in two places.

### 4. `log_end` validates the range before writing

A date before the latest start would store `end_date < start_date`, which the
adapter has to discard as malformed and which destroys the whole period record.
The handler returns `{"success": False, "message": ...}` for that case, matching
the existing failure style, and leaves stored data unchanged.

### 5. Errors use `ServiceValidationError`

It is the HA-native way to fail a service call, it surfaces in the UI and in
automations, and it does not change stored data. Messages are plain strings
today because the integration has no translation catalogue for errors; adding
one is a separate concern.

## Risks

- **Two entries, no target**: previously silent, now an error. This is the
  intended behaviour; the message says how to target.
- **Entity registry lookups** require the entities to be registered with a
  config entry, which `EntityPlatform` does for all platforms in `PLATFORMS`.
- **Device/area targets** expand through `async_extract_entity_ids`; an area
  with no entities of this integration resolves to an empty set and is treated
  as a foreign target.

## Migration

None. Existing stored rows keep their shape, and calls without a target keep
working exactly as the README documents.
