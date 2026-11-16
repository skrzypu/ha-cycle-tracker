---
id: ADR-0010
title: Service calls resolve their config entry from the call target
status: accepted
date: 2026-11-15
deciders: []
supersedes: null
superseded-by: null
related: ["ADR-0005"]
---

# ADR-0010: Service calls resolve their config entry from the call target

## Context

The integration's logging services are domain-level: they are registered once
per domain and removed on unload. Their handlers read
`ServiceCall.config_entry` to find the coordinator. That attribute does not
exist in Home Assistant 2026.1, where
`ServiceCall.__slots__ = context, data, domain, hass, return_response, service`,
so both services raised `AttributeError` before touching data.

A call carrying a `target` failed even earlier, in schema validation:
`ServiceRegistry.async_call` merges the target into the service data before
validating, and `vol.Schema` defaults to `extra=PREVENT_EXTRA`. The deleted
skeleton test suite stayed green because its fixture built a fake call object
with the invented `config_entry` attribute, so neither defect was observable.

## Decision

We will resolve the coordinator for a service call from the call's target,
using only public Home Assistant structures.

Concretely:

- Both service schemas accept optional `entity_id`, `device_id` and `area_id`.
  `services.yaml` publishes a target selector limited to
  `entity: {integration: cycle_tracker}`.
- Resolution calls
  `homeassistant.helpers.service.async_extract_entity_ids(call)`, which expands
  entity, device and area targets, then reads the entity registry to obtain
  each entity's `config_entry_id`.
- One entry id belonging to this integration resolves to that coordinator in
  `hass.data[DOMAIN]`. Several entry ids, or a target containing no entity of
  this integration, raise `ServiceValidationError`.
- No target resolves to the only coordinator in `hass.data[DOMAIN]`. Zero or
  several coordinators raise a `ServiceValidationError` that tells the user to
  target an entity of the integration.
- Services stay domain-level and are not registered per config entry.
- Handlers never read attributes that `ServiceCall` does not define. Anything
  beyond `data` and `hass` comes from public structures: the entity registry
  and `hass.data`.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Keep `ServiceCall.config_entry` (the original code) | The attribute does not exist in HA 2026.1; the handlers cannot run at all. It was only ever satisfied by a fake object in the deleted tests. |
| Scan `hass.data[DOMAIN]` and guess the entry | With more than one entry it silently picks one and can mutate the wrong user's data. Wrong should fail, not guess. |
| Register services per config entry with suffixed service names | Changes the public service surface and breaks the documented `cycle_tracker.log_start` calls; the domain-level registration is already a spec requirement. |

## Consequences

**Positive**

- The documented
  `target: entity_id: sensor.cycle_tracker_cycle_day` form works.
- A single-entry installation can still call the service without a target.
- Ambiguous or foreign targets fail loudly instead of mutating the wrong
  entry.
- Handlers depend on the real `ServiceCall` contract, so the class of defect
  that produced the skeleton tests' false green cannot recur unnoticed.

**Negative / costs**

- Every targeted call performs target expansion and entity-registry lookups
  before it does any work.
- Multi-entry installations must target explicitly; a bare call is an error
  rather than a best guess.
- Domain-level services need a lookup path to coordinators (`hass.data`)
  because the call itself carries no entry reference.

**Risks and mitigations**

- A target spans two entries of this integration: rejected with
  `ServiceValidationError`; the message names the multiple-entry case.
- A target mixes this integration's entities with entities from other
  integrations: those entities contribute their own `config_entry_id`, so the
  target can yield several entry ids and is rejected rather than resolved.
- An area or device with no entities of this integration expands to an empty
  set and is treated as a foreign target rather than as "no target".

## Follow-up

- [x] Implemented by `openspec/changes/fix-logging-services`.
- [ ] `README.md`'s Services section must describe exactly this resolution
      behaviour: target forms, the no-target single-entry case, and the
      ambiguity error.
