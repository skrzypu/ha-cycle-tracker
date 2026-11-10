---
id: ADR-0005
title: SOLID and Clean Architecture as design constraints
status: accepted
date: 2026-11-09
deciders: []
supersedes: null
superseded-by: null
related: []
---

# ADR-0005: SOLID and Clean Architecture as design constraints

## Context

Cycle Tracker is a Home Assistant custom integration written in pure Python.
Domain behavior — period records, cycle state, prediction, statistics — currently
lives inside `coordinator.py`, which is a Home Assistant class, and the stored
data is a list of dictionaries with no explicit type or invariant. Sensors,
calendar, services, and the config flow call the coordinator directly.

The project is about to grow in directions that touch the same domain from
different sides: an explicit data model, a replaceable persistence backend, a
Google Sheets store, and a Lovelace card. With the current shape, every one of
those changes edits the same framework-coupled class, and domain rules can only
be tested through Home Assistant.

## Decision

We will apply SOLID principles and Clean Architecture as design constraints for
this project, not as optional style preferences.

The dependency rule applies: source dependencies point inward, toward the
domain. The domain does not import Home Assistant, `aiohttp`, `voluptuous`, or
any storage API.

### Layers

| Layer | Responsibility | May depend on |
|---|---|---|
| Domain | Entities, value objects, invariants, prediction strategies, statistics | Nothing framework-specific |
| Application | Use cases that orchestrate domain behavior and ports | Domain |
| Ports | Narrow interfaces the application needs (repositories, clock, credentials) | Domain |
| Adapters | Home Assistant entities, services, config flow, calendar, storage, Google Sheets, HTTP | Application, ports, domain |
| Composition | Wiring adapters to use cases in `async_setup_entry` | Everything |

### SOLID mapping

- **Single Responsibility**: one use case per user action (`log_start`,
  `log_end`, refresh, import); prediction algorithms stay one strategy each.
- **Open/Closed**: new prediction algorithms are added as strategies without
  editing the coordinator; new persistence backends are added as adapters
  without editing the domain.
- **Liskov Substitution**: every implementation of a port or strategy is
  interchangeable from the caller's point of view, including error behavior.
- **Interface Segregation**: ports stay small and purpose-specific; no
  "god repository" with read, write, auth, and schema in one interface.
- **Dependency Inversion**: the application defines the ports it needs; storage
  and Google Sheets implement them; nothing in the domain knows which backend is
  active.

### Rules that follow

- Domain objects are explicit types (dataclasses or value objects), not
  dictionaries passed around.
- Invariants are enforced in the domain: end date not before start date, no
  overlapping periods, valid flow intensity, stable period identity.
- Use cases receive dependencies through their constructor; no module-level
  singletons and no service locator.
- Home Assistant payloads (entity states, service schemas, config entries) are
  mapped at the adapter boundary; domain objects never carry HA types.
- Domain tests run without a Home Assistant test harness.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Framework-first (current shape) | Domain rules stay untestable outside Home Assistant and every feature edits the same coordinator. |
| Layered architecture without the dependency rule | Layers exist on paper, but framework types leak inward and the boundary erodes. |
| Functional core / imperative shell | Compatible with this decision and allowed inside the domain; it does not replace the port and adapter boundaries. |
| Full DDD with aggregates, events, and repositories per entity | Too much ceremony for a single-user integration with one aggregate. |

## Consequences

**Positive**

- Persistence can change (local storage, Google Sheets, another backend) without
  touching domain logic.
- Domain behavior is testable in plain Python.
- Prediction algorithms and use cases stay small and independently replaceable.
- The data model becomes an explicit artifact instead of an implicit dictionary
  shape.

**Negative / costs**

- More modules and explicit mapping between domain objects and HA or sheet
  payloads.
- Risk of over-abstraction: ports with no second implementation and layers with
  no behavior.
- The existing coordinator must be migrated incrementally, so the codebase will
  temporarily contain both shapes.

**Risks and mitigations**

- Over-engineering: create a port only where a real seam exists or is planned;
  do not add a layer for a single function.
- Boundary erosion: add a cheap check that the domain package imports no Home
  Assistant or HTTP modules; keep it in pre-commit once the test suite returns.
- Migration drift: migrate one use case at a time, keeping behavior covered by
  the specs.

## Follow-up

- [ ] Define the domain data model before adding any new persistence or UI.
- [ ] Introduce the first ports (`PeriodRepository`, `Clock`) when the data
  model is settled.
- [ ] Migrate `log_start`, `log_end`, and refresh into use cases, leaving the
  coordinator as an adapter.
- [ ] Add an import-boundary check for the domain package.
