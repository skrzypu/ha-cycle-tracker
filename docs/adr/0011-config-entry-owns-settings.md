---
id: ADR-0011
title: The config entry owns settings; integration storage owns periods
status: accepted
date: 2026-11-15
deciders: []
supersedes: null
superseded-by: null
related: ["ADR-0001", "ADR-0006"]
---

# ADR-0011: The config entry owns settings; integration storage owns periods

## Context

The coordinator copied `cycle_length`, `period_length`, `prediction_algorithm`
and the notification settings from `entry.data` into its store on the first
load only. From then on the stored copy won, so later changes to the entry were
never observed. The options flow writes `entry.options`, which nothing read.
Changing any setting therefore had no effect on any entity.

This left two writable copies of the same configuration, one of them invisible
to the user interface, with no rule for which copy is authoritative.

## Decision

We will make the config entry the single source of truth for configuration and
keep integration storage for recorded periods only.

Concretely:

- Every configurable setting is resolved at read time by one resolver:
  `entry.options` → `entry.data` → module default. Getters, the prediction
  config and the options-form defaults all use it.
- Integration storage holds `{"periods": [...]}` and no settings.
  `_async_update_data` normalizes whatever it loads to that shape, so setting
  keys left in older stored data are dropped from memory and disappear on the
  next save.
- The entry's update listener already reloads the entry after an options
  change, so settings are re-read on the next setup. No extra refresh
  mechanism is added.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Have the options flow write settings into the store | Creates two sources of truth that can disagree, and requires a migration for existing installations. The entry was already the origin of the values, so the stored copy added nothing. |
| Adopt `OptionsFlowWithReload` and drop the update listener | A larger lifecycle change than the defect required. It is a possible follow-up, not part of this decision. |

## Consequences

**Positive**

- Options changes take effect after the entry reloads.
- One rule explains every setting's value: options, then data, then default.
- Stored data contains only periods, so its shape matches the domain model in
  ADR-0006.

**Negative / costs**

- Settings read from legacy stored data are ignored rather than migrated. They
  were copies of `entry.data`, so no user value is lost, but the stored keys
  are dropped on the next save.
- A setting cannot be cleared back to "unset" from the dialog, because
  `entry.data` is never rewritten and remains the fallback.
- The reload is the only propagation path; changing settings outside the
  config entry does not trigger it and leaves entities on the old values.

**Risks and mitigations**

- Downgrading to code that re-seeds settings from `entry.data` restores the
  original setup values; that is the same data the copy came from.
- Writing settings outside the config entry (for example, editing stored data
  directly) bypasses the reload. Keep settings in the entry and let the
  options flow update it.
- Stored legacy settings are dropped silently. This is intentional and loses
  no unique data; revisit only if a future store field cannot be recomputed
  from the entry.

## Follow-up

- [x] Implemented by `openspec/changes/fix-options-flow-and-lifecycle`.
- [ ] Consider `OptionsFlowWithReload` and removal of the update listener as a
      separate lifecycle decision.
