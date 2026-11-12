# Design

## Context

Documentation lives in plain Markdown across `README.md`, `docs/adr/`,
`docs/bdr/`, `docs/design/`, and `docs/ideas/`. Decision records use a YAML
frontmatter plus prose and tables; no diagram appears anywhere in the project's
own docs today. The prediction rules are fully decided (BDR-0004) but only
described in prose.

GitHub renders Mermaid fenced blocks natively. Obsidian-specific syntax
(`[[wikilinks]]`, `![[embeds]]`) does not render on GitHub; PlantUML needs a
Kroki server. These constraints decide the approach below.

## Goals / Non-Goals

**Goals:**
- Make the prediction model readable at a glance and verifiable by a reviewer.
- Give end users a self-contained explanation of how the algorithms work.
- Keep every diagram source portable so it renders identically on GitHub and,
  later, in any static site without rewriting.

**Non-Goals:**
- No generated documentation site (mkdocs) or Obsidian vault structure.
- No changes to code, specs, or system behavior.
- No diagram tooling in CI; rendering is left to GitHub.
- No localization of the guide (English first, consistent with the card).

## Decisions

### 1. Mermaid is the only diagram language

All diagrams are ` ```mermaid ` fenced blocks in portable Markdown.

- **Alternatives considered:**
  - *PlantUML / graphviz* — needs a server or plugin; GitHub does not render
    them natively. Rejected.
  - *Obsidian syntax* — `[[ ]]` and `![[ ]]` break GitHub rendering. Rejected
    as a source format; Obsidian may still be used as a local *viewer* on the
    same files.
  - *ASCII diagrams* — render everywhere but are brittle to maintain and
    cannot express date ranges. Used only in prose, never as the source of
    truth.
- Mermaid renders on GitHub, in mkdocs Material (via `pymdownx.superfences`),
  and in Obsidian, so the same source serves all three without conversion.

### 2. Diagram inventory and types

| Location | Diagram | Mermaid type |
|---|---|---|
| `docs/guide/algorithms.md` | Cycle phases and their order | `timeline` |
| `docs/guide/algorithms.md` | Prediction derivation (cycles -> algorithm -> date -> windows -> confidence) | `flowchart LR` |
| `docs/guide/algorithms.md` | Confidence bands (low/medium/high) | `flowchart LR` |
| `docs/bdr/0004-*.md` | Prediction windows on a cycle timeline | `gantt` |
| `docs/adr/0005-*.md` | Dependency rule (adapters -> use cases -> domain) | `flowchart LR` |
| `docs/adr/0006-*.md` | Domain entities | `classDiagram` |

The BDR-0004 window diagram uses `gantt` with an example cycle because it
expresses overlapping date ranges (uncertainty ±1 sigma, ovulation centre −14
days ±2, fertile five-days-before-through-ovulation) that a flowchart cannot.
The window *derivation* (how one value leads to the next) is a flowchart, kept
separate from the *position* of windows on a timeline.

### 3. User guide lives in `docs/guide/`, not in the README

- `README.md` stays the front door and gains a "User guide" link.
- `docs/guide/algorithms.md` holds the phase timeline and the full prediction
  explanation with diagrams, so the whole algorithm story can be sent to a
  reviewer as one file.
- **Alternatives considered:** extending the README (rejected: already 246
  lines and mixes user and developer audiences); a separate mkdocs site
  (rejected in the proposal).

### 4. The documentation decision is recorded as ADR-0009

The choice to use Mermaid in portable Markdown with no generated site is a
durable decision that outlives this change. It is recorded as
`docs/adr/0009-documentation-mermaid-portable-markdown.md` (authored by the
decision-recorder agent) so a future contributor does not re-litigate
"should we adopt mkdocs/Obsidian".

## Risks / Trade-offs

- [Mermaid `gantt` is fiddly with day-offsets and looks cluttered with
  date labels] -> Keep the window diagram to a single illustrative cycle with
  a fixed 28-day example; state in the caption that lengths vary per user.
- [A reviewer needs Mermaid-aware tooling to see rendered output] -> GitHub
  renders it, so a shared link suffices; the raw source is also readable as
  text.
- [Diagrams drift from the decision text as BDR-0004 evolves] -> The diagram
  restates the same rules already in the decision; any rule change must update
  both, noted in the ADR-0009 follow-up.
- [Confidence formula is dense in a flowchart] -> Keep the formula as inline
  text beside the band flowchart rather than forcing it into nodes.
