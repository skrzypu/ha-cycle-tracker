---
id: ADR-0017
title: Verification-found test gaps are closed before archive, preferring E2E
status: accepted
date: 2026-11-20
deciders: []
supersedes: null
superseded-by: null
related: ["ADR-0012", "ADR-0016", "BDR-0004"]
---

# ADR-0017: Verification-found test gaps are closed before archive, preferring E2E

## Context

Verification of an OpenSpec change (`/opsx-verify`) and code review can both
surface a scenario that has no dedicated test. The verification is advisory:
it reports the gap but does not block the change. A gap that is reported and
then archived leaves the shipped contract unguarded, so the verification adds
no durable value.

During verification of the change `insert-new-rows-at-top`, one scenario in the
sheet-sync delta spec had no dedicated test: "Same-day start updated". Before
the change was archived, an E2E regression test was added at
`tests/e2e/test_period_open_flow.py::test_same_day_repeat_updates_the_open_row_instead_of_appending`;
it calls `log_start` twice with the same date and asserts one persisted row with
the updated flow and one tracked period through entities. The full
`pre-commit` gate stayed green.

The E2E boundary is already defined in `tests/e2e/conftest.py`: history enters
only through the `log_start`/`log_end` services, and results are read from
entity states and the calendar component's `get_events` service.
`tests/e2e/test_persistence_flow.py` is the established exception that proves
persistence directly. ADR-0012 sets the quality bar for E2E tests (public
surface, literal expectations, mutation-proven strength), and BDR-0004 makes
the prediction a health-adjacent promise to users.

## Decision

We will close any test gap identified by verification of an OpenSpec change or
by code review before that change is archived — unless the user explicitly
accepts the gap.

- A reported gap blocks archival until a dedicated test covers the scenario or
  the user records an explicit acceptance of the gap in the change.
- When adding the test, prefer an end-to-end test that enters state through the
  public services (`log_start`/`log_end`) and observes results through entities
  and the calendar, over an adapter-only unit test. The boundary and its
  persistence-proof exception are those documented in `tests/e2e/conftest.py`
  and `tests/e2e/test_persistence_flow.py`.
- The added test must preserve the intent of the scenario. Existing assertions
  are not weakened or removed to make coverage appear complete; new tests
  follow the E2E quality bar in ADR-0012.
- An accepted gap is an exception, not a precedent: it is recorded in the
  change with the reason, and the scenario stays visible for a later change.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Archive the change with the gap noted as a follow-up | The note is easy to lose; verification would report findings nobody acts on. |
| Add an adapter-only unit test for speed | Covers one adapter, not the shipped contract across services, entities and calendar. |
| Loosen or drop existing assertions so the scenario "passes" | Makes coverage look complete while removing the constraint the test existed to enforce. |
| Make verification blocking and fail the change automatically | Advisory verification is useful because it reports gaps for a human to judge; an explicit acceptance must remain possible. |

## Consequences

**Positive**

- Every advisory finding is either fixed or explicitly accepted, so verification
  has a visible outcome before archive.
- New regression tests enter through the public surface and protect the shipped
  contract, consistent with ADR-0012.
- Scenario intent is preserved; the suite does not accumulate weakened tests.

**Negative / costs**

- Archival can be delayed by the time needed to write a strong E2E test.
- E2E tests are slower and more brittle than adapter units, and must obey the
  determinism and mutation requirements of ADR-0012.
- Accepted gaps need to be tracked so they are not silently forgotten.

**Risks and mitigations**

- A gap could be closed with a nominally E2E test that reaches into internals.
  Mitigate by the `tests/e2e/conftest.py` boundary and the mutation check from
  ADR-0012.
- "Explicit user acceptance" could become a rubber stamp. Mitigate by requiring
  the reason to be recorded in the change.
- The health-adjacent promise in BDR-0004 raises the cost of an unguarded
  scenario; prefer the E2E test whenever the scenario touches the user-visible
  contract.

## Follow-up

- [x] Keep the `insert-new-rows-at-top` change and its E2E regression test linked
      when the change is archived. Closed 2026-11-20: archived at
      `openspec/changes/archive/2026-11-20-insert-new-rows-at-top/` (delta synced
      to `openspec/specs/sheet-sync/spec.md`, strict validation passed); covered
      by `tests/e2e/test_period_open_flow.py::test_same_day_repeat_updates_the_open_row_instead_of_appending`
      (E2E 20 passed; `pre-commit run --all-files` exit 0).
- [ ] Apply the same gap-before-archive check to future `/opsx-verify` runs.
