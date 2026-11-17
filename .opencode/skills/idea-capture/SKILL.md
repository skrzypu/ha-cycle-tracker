---
name: idea-capture
description: Capture a new idea into the project idea backlog (docs/ideas/) using the canonical template and lifecycle. Use when the user wants to write down, park, or record an idea, or asks "add this to the ideas", "capture this idea", or "park this thought".
---

Capture an idea into `docs/ideas/` without deciding it.

**Not a decision.** An idea is a parking-lot entry, not a commitment. It never
overrides `openspec/specs/`, `docs/adr/`, or `docs/bdr/`. Capturing an idea is
the whole job — do not implement it, promote it, or write an ADR/BDR for it.

## Template source

`docs/ideas/README.md` is the single source of truth for the template, the
lifecycle, and the rules. Read it before writing and follow it verbatim. If the
template here and the file disagree, the file wins.

## Lifecycle

| Status | Meaning |
|---|---|
| `idea` | Captured, not examined. No effort spent yet. |
| `exploring` | Being researched or discussed. Open questions listed. |
| `decided` | Promoted to an ADR, BDR, or OpenSpec change. Link it. |
| `parked` | Deliberately postponed. Reason recorded. |
| `rejected` | Will not be pursued. Reason recorded. |

A new capture starts at `idea` unless the user says otherwise.

## Template

```markdown
### I-000: Short title

- **Status:** idea | exploring | decided | parked | rejected
- **Problem:** what hurts today
- **Idea:** what we would do
- **Value:** who benefits and how
- **Constraints / conflicts:** ADRs, specs, effort, privacy
- **Dependencies:**
  - ADR-0000 / BDR-0000 / I-000 / `change-name` — known
  - something unconfirmed — dependency unknown
- **Open questions:** what must be answered before deciding
- **Decision:** link to ADR/BDR/change, or the reason for parked/rejected
```

## Where it goes

- One file per theme, not per idea (`card-and-sync.md`, `period-logging.md`, …).
- Append a new `### I-###` entry to the theme file; allocate the next free ID by
  reading the existing entries, never by guessing.
- If no theme fits, create a new theme file, add it to the index table in
  `docs/ideas/README.md`, and say so when you report back.
- Update the index row's status only when the entry's status differs from it.

## Dependency rule

Every dependency line ends with `— known` or `— dependency unknown`.

- `known` — the reference exists **and** the idea genuinely depends on it.
  Verify the reference before writing `known`: the ADR/BDR file exists under
  `docs/adr/` or `docs/bdr/`, the idea ID exists in the backlog, or the change
  exists under `openspec/changes/` (including `openspec/changes/archive/`).
- `dependency unknown` — the idea might depend on something not yet confirmed,
  or the reference cannot be found. Say what is unconfirmed in the line.

Never write `known` for a reference you did not check. When the idea has no
dependencies at all, write `- **Dependencies:** none`.

## Output

Report back: the file touched, the new entry ID and title, its status, and any
dependency left as `dependency unknown` with the reason. Do not summarise the
whole backlog.
