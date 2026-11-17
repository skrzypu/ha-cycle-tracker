# Design

## Context

The idea backlog is a parking lot, not a decision store: ideas live in theme
files (`card-and-sync.md`, `period-logging.md`, …), one `### I-###` entry each,
following a template and lifecycle (`idea → exploring → decided → parked →
rejected`) in `docs/ideas/README.md`. Entries link to ADRs/BDRs but the decision
lives there, not in the backlog.

The project already has two kinds of agent skill: installed skills.sh skills
(pinned in `skills-lock.json`, indexed in `docs/skills/README.md`, governed by
ADR-0013) and project-local skills (`.opencode/skills/<name>/SKILL.md`, e.g.
`openspec-propose`). Native subagents live in `.opencode/agent/<name>.md`.

## Goals / Non-Goals

**Goals:**

- One source of truth for how an idea is captured.
- Record an idea's dependencies so prerequisites are explicit, not implied.

**Non-Goals:**

- Changing the idea lifecycle or the theme-file layout.
- Turning idea capture into an installed skills.sh skill.
- Deciding or promoting ideas — only capturing them.

## Decisions

**1. Add a `Dependencies` field to the template.**
Each entry gains `- **Dependencies:**`, a list of references, each marked
`— known` or `— dependency unknown`. "Known" means the reference exists and the
idea genuinely depends on it; "dependency unknown" means the idea might depend
on something not yet confirmed (for example whether I-008 requires I-007).
Rationale: distinguishes a real blocker from an unverified one, and feeds the
"order of work" section in `docs/ideas/README.md`.

**2. The skill is project-local, not installed.**
`.opencode/skills/idea-capture/SKILL.md`, beside the existing `openspec-*`
skills. Rationale: the convention is specific to this project's `docs/ideas/`
format; an installed skills.sh skill would add pinning and index review
(ADR-0013) for something only this repo uses. Alternative rejected: a skills.sh
skill.

**3. A dedicated subagent is warranted.**
`.opencode/agent/idea-capture.md`, `mode: subagent`, write limited to
`docs/ideas/**`, with read access to `docs/adr/**` and `docs/bdr/**` for
dependency links. Rationale: idea capture is recurring and bounded, and the
project already runs narrow native subagents (`agent-auditor`). Alternative
rejected: folding into `docs-writer`, which is general prose and would not
enforce the dependency rule. The exact `model` is selected at apply time via
`opencode models`.

## Risks / Trade-offs

- [The skill/agent drift from the template] → the skill references the template
  in `docs/ideas/README.md` as the single source; `agent-auditor` cross-checks
  agent claims against the repo.
- [A "known" dependency that does not actually exist] → the skill instructs the
  agent to verify the referenced ADR/BDR/idea/change file exists before marking
  it known; otherwise it stays `dependency unknown`.

## Migration Plan

None. The new field is additive; existing entries simply lack it.

## Open Questions

None blocking. (Backfilling existing entries with `Dependencies` is optional
cleanup and deliberately out of scope.)
