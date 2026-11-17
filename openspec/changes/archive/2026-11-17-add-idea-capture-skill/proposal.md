# Proposal

## Why

Ideas arrive faster than decisions, and the idea backlog (`docs/ideas/`) is how
the project separates thinking from deciding. Today the idea template has no
place to record what an idea depends on, so an idea's prerequisites — an ADR,
another idea, a parked change — stay implicit and ordering work is guesswork.
Capture is also done ad hoc, so entries drift from the template.

## What Changes

- Add a `Dependencies` field to the idea template in `docs/ideas/README.md`.
  Known dependencies (BDRs, ADRs, other ideas, parked changes) are listed; a
  dependency that is not yet confirmed is marked `dependency unknown`.
- Add a project-local skill `idea-capture` that encodes the capture convention:
  the idea lifecycle, the template, and the dependency rule.
- Add a subagent `idea-capture` that applies the skill to capture a new idea
  consistently, scoped to the idea backlog and the decision records it links to.

## Capabilities

### New Capabilities

None — this is tooling and documentation only; no system behavior changes.

### Modified Capabilities

None.

## Impact

- `docs/ideas/README.md` — the template gains a `Dependencies` field.
- `.opencode/skills/idea-capture/SKILL.md` — new project-local skill.
- `.opencode/agent/idea-capture.md` — new subagent definition.
- No code, spec, dependency, or `skills-lock.json` changes.
