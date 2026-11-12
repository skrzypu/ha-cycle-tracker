# Proposal

## Why

The project's durable decisions (BDR/ADR) and its only user-facing algorithm
description are prose with tables, so the product's core promise — how a
prediction becomes a window, not a date — is hard to read at a glance and hard
to hand to a reviewer for verification. There is no user-facing explanation of
how the prediction algorithms work, only the thin "Prediction" section of the
README and the internal `docs/ideas/prediction-algorithms.md`.

## What Changes

- Adopt **Mermaid** as the single diagram language for all documentation, kept
  in portable Markdown so diagrams render natively on GitHub (no generated
  site: no mkdocs, no Obsidian-specific syntax). This is recorded as a durable
  decision (ADR-0009).
- Add a diagram to **BDR-0004** (prediction is a window, not a date) showing
  the uncertainty, ovulation, and fertile windows.
- Add a diagram to **ADR-0005** (SOLID / Clean Architecture) showing the
  dependency rule (adapters -> use cases -> domain).
- Add a diagram to **ADR-0006** (domain model contract) showing the domain
  entities as a class diagram.
- Create a new user-facing guide at `docs/guide/algorithms.md` explaining the
  cycle phases and how the next-period prediction, uncertainty window,
  ovulation window, fertile window, and confidence are derived, with Mermaid
  diagrams.
- Link the guide from `README.md`.

## Capabilities

### New Capabilities

None. This is a pure documentation change; it changes no system behavior, so
`skip_specs: true` is set in `.openspec.yaml`.

### Modified Capabilities

None.

## Impact

- **Documentation only**: `docs/bdr/0004-*.md`, `docs/adr/0005-*.md`,
  `docs/adr/0006-*.md`, new `docs/guide/algorithms.md`, new `docs/adr/0009-*.md`,
  and a link in `README.md`.
- **No code, no specs, no API, no dependency changes.**
