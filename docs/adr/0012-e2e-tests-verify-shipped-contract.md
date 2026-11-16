---
id: ADR-0012
title: E2E tests verify the shipped contract, and their strength is proven by mutation
status: accepted
date: 2026-11-16
deciders: []
supersedes: null
superseded-by: null
related: ["ADR-0005", "ADR-0006"]
---

# ADR-0012: E2E tests verify the shipped contract, and their strength is proven by mutation

## Context

Cycle Tracker is a Home Assistant custom integration written in pure Python with
three test layers:

- `tests/domain` — framework-free algorithm tests, imported via `sys.path` and
  guarded by an AST import-boundary test.
- `tests/adapters` — one adapter at a time, against `hass` with
  `pytest-homeassistant-custom-component`.
- `tests/e2e` — being written now: a `MockConfigEntry` is set up in `hass`,
  history is recorded only through the `cycle_tracker.log_start` and
  `cycle_tracker.log_end` service calls, and the tests assert sensor states,
  attributes and calendar events.

Most of these tests are written by AI agents. The stated concern is whether
high-quality E2E tests can be guaranteed at all: a reviewer reading a test
cannot tell whether it constrains the integration or merely restates its
implementation. Coverage does not answer that question — a test can execute
every line and still pass after the wiring is removed.

The shipped contract is `docs/guide/algorithms.md` plus the entity table in
`README.md`. ADR-0005 keeps the domain framework-free and ADR-0006 fixes the
domain model, so the domain cannot be the E2E suite's entry point.

## Decision

We will treat the E2E suite as a test of the documented contract and prove each
test's strength with a targeted mutation instead of trusting the author's
judgment.

1. **Public surface only.** An E2E test drives `hass`, a real config entry, the
   entity registry, the calendar entity and the registered services. It does
   not import `custom_components.cycle_tracker.domain` and does not call domain
   functions.
2. **Literal expectations.** Expected values are literals taken from the
   documented contract (`docs/guide/algorithms.md`, README entity table), never
   recomputed by the implementation under test. An expectation computed by the
   code it checks proves nothing.
3. **Journeys, not branches.** E2E covers: fresh install (prediction entities
   `unknown`), first usable prediction, algorithm selection changing the
   predicted date, a gap over 90 days restarting the history window, a late
   period that does not move the predicted date, and a restart that re-reads
   storage and reproduces identical entity states. Edge cases stay in the
   domain tests.
4. **Determinism is a review requirement.** No sleeps, no network, the clock is
   frozen, storage is the only persistence, and a failure is reproducible
   locally with a single command.
5. **Test strength is demonstrated, not claimed.** For a new or changed E2E
   test, break one production line the test is supposed to cover — shift a
   threshold, swap a strategy default, drop an attribute — confirm the test
   fails, then restore. Record the mutation that was killed in the change
   description or PR text. An E2E test that survives its own targeted mutation
   is rewritten or deleted.
6. **Review gate.** A test that would pass with the integration's wiring
   removed is a defect, not a weak test. Reviewers ask for the mutation
   evidence, not for a coverage number. Coverage may not be used as the quality
   argument.
7. **This is how AI-written E2E tests are kept honest.** The quality lives in
   the constraints — literal expectations from the docs, public surface only, a
   killed mutation, determinism — not in the author's judgment. Where a human
   cannot eyeball the difference, the mutation check is the objective test.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Assert against domain functions called directly from the E2E test | The test would prove the domain, which is already covered in `tests/domain`, and would bypass the wiring E2E exists to check. |
| Compute expectations with the implementation under test | Tautological: any bug becomes the expected value. The failure mode is invisible in review. |
| Gate quality on a coverage threshold | Coverage measures execution, not constraint. It cannot distinguish a test from a restatement. |
| One E2E test per branch, mirroring the domain suite | Slow, brittle, and duplicates tests that already run framework-free. |
| Rely on human review of test code alone | Does not scale with the volume of AI-written tests; a plausible-looking test and a real one read the same. |

## Consequences

**Positive**

- The E2E suite checks what the project promises users, not how the code is
  currently organized, so refactors inside a layer do not force rewrites.
- The mutation check gives a reviewer a concrete, falsifiable artifact instead
  of an opinion about test quality.
- A test that cannot fail for the right reason is removed, so the suite does
  not accumulate confident-looking dead weight.
- Determinism makes failures actionable by anyone, in CI or locally.

**Negative / costs**

- Mutation checking is manual and costs a few minutes per new or changed test.
- Literal expectations have to be maintained when the contract changes on
  purpose; updating them is a deliberate act, not a regeneration.
- The E2E suite stays small on purpose, so some wiring — option resolution,
  storage shape, entity registration details — can only be caught by the
  adapter tests, and journeys do not localize failures as precisely as units.

**Risks and mitigations**

- A mutation can be chosen to match what the test already asserts, making the
  check vacuous. Mitigation: mutate the line named in the test's intent, and
  prefer mutations that change a user-visible value.
- Literal expectations can drift from the docs after a contract change.
  Mitigation: the contract change and the expectation update are one change.
- Running the suite with the clock frozen can hide timezone and DST handling.
  Mitigation: those cases belong to the domain and adapter layers, which can
  vary the clock.

## Follow-up

- [ ] Link the OpenSpec change that introduces `tests/e2e/` once it lands.
- [ ] Document the single-command local reproduction once the suite is complete.
