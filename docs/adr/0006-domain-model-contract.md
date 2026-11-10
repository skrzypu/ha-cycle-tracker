---
id: ADR-0006
title: Explicit, framework-free domain model contract
status: accepted
date: 2026-11-10
deciders: []
supersedes: null
superseded-by: null
related: ["ADR-0001", "ADR-0005"]
---

# ADR-0006: Explicit, framework-free domain model contract

## Context

The domain currently exists only as a list of dictionaries inside
`coordinator.py`; fields, identity, and invariants are implicit. ADR-0005
requires an explicit, framework-free domain with the dependency rule pointing
inward, so the data model has to be settled before any new persistence backend,
service, or UI is added.

The prediction algorithms define what the model must contain: a prediction is a
pure function of the period history, a reference date, and the configured
algorithm. The reasoning and open product questions live in
`docs/ideas/domain-model.md` and `docs/ideas/prediction-algorithms.md`; this
record fixes the model those documents converge on.

## Decision

We will model the domain as explicit value objects in which only periods are
stored and everything else is derived on read.

**Stored entity.** `Period` is the only stored entity: `id` (UUID generated
once at creation, stored as `period_id`, surviving date edits), `start` (date),
`end` (`date | None`), `flow` (`spotting | light | medium | heavy | None`),
`notes` (free text, no domain length limit), and `updated_at`
(`datetime | None`). There is no `created_at`; no `source` in the domain —
origin is an adapter concern.

**Derived, never persisted.** `Cycle` (a pair of consecutive period starts,
`length_days` start-to-start); `Prediction` (next period date, uncertainty
window, ovulation window, fertile window, confidence value and band, late flag,
warnings tuple); cycle-length statistics; phase boundaries.

**Invariants.** Hard errors only: `end` before `start`; overlapping periods;
`log_start` while a period is open; a new `period_id` reusing an existing start
date. Everything else is a warning, never a silent repair: an unusually long
period, missing flow, a cycle outside the 15–90 day bounds, or a gap longer
than 90 days. Identity decides duplicates: an existing `period_id` is an update
even if its dates changed.

**Open periods.** Exactly one period may be open, with no duration limit.
`log_end` closes it; the model never invents an end date.

**Time.** Calendar dates, not instants. "Today" comes from a `Clock` port;
nothing calls `date.today()`.

**Ports.** Minimum `PeriodRepository` (read all, upsert, delete) plus `Clock`.
The algorithm name and outlier bounds are use-case arguments from
configuration, not ports.

**Warnings.** A domain value object with kind (`outlier`, `gap`,
`missing_flow`) plus the offending period id. The adapter decides whether that
becomes a repair issue, a sensor attribute, or a log line.

**Migration.** None. The integration has not shipped usable data; the old
`{start_date, end_date}` dictionaries are discarded.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Dictionaries passed around (current shape) | No type, identity, or invariant; every caller guesses the shape and domain rules cannot be tested outside Home Assistant. |
| Stored `Cycle` entity | A cycle is fully determined by two consecutive starts; storing it duplicates state and can disagree with the period list. |
| Deterministic hash or start-date identity | A date correction would create a new identity, breaking updates and adapter row mapping; a reused date would silently merge rows. |
| Auto-closing a previous open period | Invents data the user did not enter; a hard error forces the user to close the period explicitly. |
| Auto-correcting invalid data | Hides typos and real anomalies and makes the history disagree with what the user recorded. |
| A single "store" port | Violates interface segregation and the dependency rule; read, write, and time are different seams. |
| Migrating the old store | There is no shipped usable data, so migration code would add risk with no user benefit. |

## Consequences

**Positive**

- The domain is explicit and testable in plain Python, without Home Assistant.
- Sheet and Home Assistant payloads are mapped at the adapter boundary, so the
  model stays stable across backends.
- Invariants and warnings have one home instead of being scattered across
  callers.

**Negative / costs**

- More modules and explicit mapping code between domain objects and HA or sheet
  payloads.
- The coordinator migration is incremental, so both shapes coexist temporarily.

**Risks and mitigations**

- Over-abstraction: add a port only where a seam is real or planned; the
  algorithm name and bounds stay use-case arguments rather than ports.
- Derived state drifting from stored periods: derive on read, never cache a
  `Cycle` or `Prediction` in persistence.
- Migration drift: move one use case at a time, keeping behavior covered by the
  specs.

## Follow-up

- [ ] Implement `Period`, `Cycle`, `Prediction`, and the warning value object in
      the domain package.
- [ ] Add `PeriodRepository` and `Clock` ports and cover the invariants with
      domain tests.
- [ ] Migrate `log_start`, `log_end`, and refresh into use cases, leaving the
      coordinator as an adapter (see ADR-0005 follow-up).
- [ ] Update the specs to match the model before the adapter swap.
