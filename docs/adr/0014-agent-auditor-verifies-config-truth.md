---
id: ADR-0014
title: An agent auditor periodically verifies that agent and config documentation is still true
status: accepted
date: 2026-11-16
deciders: []
supersedes: null
superseded-by: null
related: ["ADR-0013"]
---

# ADR-0014: An agent auditor periodically verifies that agent and config documentation is still true

## Context

The project tells its agents how to work through several files: the native
agent prompts in `.opencode/agent/`, the per-agent append prompts in
`.opencode/oh-my-opencode-slim/`, the architecture and business decisions in
`docs/adr/` and `docs/bdr/`, the skills index in `docs/skills/README.md`, the
algorithm contract in `docs/guide/` and the entity table in `README.md`.

These files go stale and wrong without anyone noticing. A token-cost audit
found, in a prompt that loads into every `oracle` invocation, a block of
"pre-seeded" architecture decision records numbered 001–005 that do not exist
in `docs/adr/` and contradict the shipped code (a `weighted moving average`
weight scheme and a "all prediction in `coordinator.py`" layout that were both
replaced by the `domain/` package). The same audit found a cost/model table
naming model IDs that `opencode models` does not list. ADR-0013 made skills
reviewable through an index, but nothing checks that the prompts themselves, or
the decisions they cite, are still true.

Agents generate plausible prose, so a false claim in a prompt reads exactly
like a true one. The failure mode is silent drift, not a crash.

## Decision

We will add one read-only native agent, `@agent-auditor`, whose only job is to
detect that drift.

- The agent cross-checks the prompt, decision, skills-index and guide files
  listed above against the actual code (`custom_components/`, `tests/`,
  `openspec/`) and, for model IDs, against `opencode models`.
- It reports a table of `file:line → claim → verdict → evidence`, where the
  verdict is one of `stale`, `duplicate`, `fabricated` or `contradiction`, and
  ends with a single line stating whether anything needs human action.
- It never edits anything; its permissions are `read`, `glob` and `grep` only.
- It runs on request ("audit agents") and is required before any change to the
  agent system (adding, removing or re-prompting an agent, or re-pinning a
  skill). It is not on a timer: OpenCode has no scheduler, and a stale audit is
  itself a false claim.

## Consequences

**Positive**

- Fabricated or superseded claims in prompts are caught by a process, not by
  whoever happens to read the file.
- The audit is cheap: a free model, read-only tools, and a report format that
  is one table, not prose.
- It completes ADR-0013: the skills index is reviewable, and now the truth of
  the whole agent/documentation surface is verifiable.

**Negative / costs**

- The auditor runs only when asked or before a config change, so drift can
  still sit for a while between audits.
- It is an agent too, so its own prompt and scope can drift; it remains subject
  to the same human review as the files it checks.
- Cross-checking model IDs requires running `opencode models`, which it must do
  rather than trust the config file's spelling.

## Follow-up

- [ ] Run `@agent-auditor` after the next model or agent change and record the
      result in the change's description.
