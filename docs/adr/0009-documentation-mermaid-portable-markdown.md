---
id: ADR-0009
title: Documentation uses Mermaid diagrams in portable Markdown
status: accepted
date: 2026-11-12
deciders: []
supersedes: null
superseded-by: null
related: []
---

# ADR-0009: Documentation uses Mermaid diagrams in portable Markdown

## Context

The project's documentation (README, `docs/adr`, `docs/bdr`, `docs/ideas`) is
prose plus tables; no diagram appears anywhere. Key decisions such as BDR-0004
(prediction is a window, not a date) are hard to read at a glance and hard to
hand to a reviewer for verification. There is no user-facing explanation of how
the prediction algorithms work.

Diagrams must stay readable where the documentation already lives: the GitHub
repository, a local editor, and any future site. That rules out formats that
need a rendering service or a plugin just to display the source.

## Decision

We will use Mermaid fenced code blocks as the single diagram language across all
documentation, kept in portable Markdown so diagrams render natively on GitHub.

Concretely:

- Every diagram is a Mermaid fenced code block in a Markdown file.
- Do not introduce a generated documentation site (mkdocs) or Obsidian-specific
  syntax (`[[wikilinks]]`, `![[embeds]]`) as the source format.
- Obsidian may be used only as a local viewer over the same portable files.
- Plain-ASCII diagrams may appear inline in prose but are never the source of
  truth.

## Alternatives considered

| Alternative | Why not |
|---|---|
| PlantUML / Graphviz | Needs a server or plugin to render; GitHub does not render it natively. Rejected. |
| Obsidian vault with wikilinks | Breaks GitHub rendering; rejected as a source format. Obsidian remains usable as a local viewer. |
| mkdocs Material generated site | Adds config and CI for a site GitHub already largely covers. Deferred, not rejected; the portable source migrates cleanly if a site is wanted later. |

## Consequences

**Positive**

- A single source of truth renders on GitHub, in mkdocs, and in Obsidian.
- Decisions such as BDR-0004 and the domain model become readable at a glance
  and easier to hand to a reviewer.
- The documentation has a stated place for the prediction algorithms to be
  explained visually.

**Negative / costs**

- Mermaid gantt is fiddly for date windows, so such diagrams stay illustrative
  with a caption stating real values come from the user's history.
- Diagrams are additional artifacts to keep in sync with the prose.

**Risks and mitigations**

- Prose and diagram drift apart: any change to a documented rule must update
  both the prose and its diagram.
- A diagram is mistaken for a precise specification: gantt windows carry an
  explicit caption pointing to the user's history as the source of real values.

## Follow-up

- [x] Added the prediction-window diagram to BDR-0004.
- [x] Added the dependency-direction diagram to ADR-0005.
- [x] Added the domain-model class diagram to ADR-0006.
- [x] Add a user-facing explanation of the prediction algorithms with its
      diagram — `docs/guide/algorithms.md`.
- [ ] Keep the prose and each diagram in sync whenever a documented rule
      changes.
