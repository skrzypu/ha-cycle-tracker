# Tasks

## 1. Record the documentation decision

- [x] 1.1 Create `docs/adr/0009-documentation-mermaid-portable-markdown.md` (via the decision-recorder agent) recording that diagrams use Mermaid in portable Markdown with GitHub-native rendering and no generated site (Obsidian/mkdocs); verify the file has the standard ADR frontmatter and is listed in `docs/adr/README.md` index.

## 2. Add diagrams to existing decision records

- [x] 2.1 Add a Mermaid `gantt` diagram to `docs/bdr/0004-prediction-is-a-window-not-a-date.md` showing the uncertainty, ovulation, and fertile windows on a single illustrative cycle; verify the block is a valid ` ```mermaid ` fence with no non-Mermaid markup and the prose still states the same rules.
- [x] 2.2 Add a Mermaid `flowchart LR` to `docs/adr/0005-solid-and-clean-architecture.md` showing the dependency rule (adapters -> use cases -> domain); verify the diagram direction matches the ADR's dependency-rule text.
- [x] 2.3 Add a Mermaid `classDiagram` to `docs/adr/0006-domain-model-contract.md` showing `Period`, `Cycle`, and `Prediction` with their fields and the derived-from relationships; verify field names match the ADR-0006 model exactly.

## 3. Write the user-facing algorithm guide

- [x] 3.1 Create `docs/guide/algorithms.md` with a `timeline` diagram of the cycle phases, a `flowchart LR` of the prediction derivation (last 6 cycles -> algorithm -> predicted length -> next period -> windows), and a `flowchart LR` of the confidence bands, plus prose that matches BDR-0004's rules (mean / weighted moving average / median, uncertainty ±1 sigma with ±2-day floor, ovulation at next period −14 days ±2, fertile five-days-before-through-ovulation, confidence `min(1, 1 − σ/mean) × min(1, n/6)` with bands 0.4/0.7); verify the guide renders as standalone Markdown with no broken relative links and the algorithm values match `docs/ideas/prediction-algorithms.md`.

## 4. Link the guide and verify

- [x] 4.1 Add a "User guide" link from `README.md` to `docs/guide/algorithms.md` in the appropriate section; verify the link resolves to the created file.
- [x] 4.2 Review all four decision-record edits and the new guide in GitHub's rendered view; verify every Mermaid block renders (no red "diagram syntax error") and no Obsidian-specific syntax (`[[ ]]`, `![[ ]]`) was introduced.
