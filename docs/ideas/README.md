# Idea Backlog

A parking lot for ideas that are not decisions yet. Nothing here is a
commitment, and nothing here overrides `openspec/specs/` or `docs/adr` /
`docs/bdr`.

## Why this exists

Ideas arrive faster than decisions. Without a place for them they either get
implemented by accident or get lost. This folder separates **thinking** from
**deciding**: an idea is written down cheaply, explored when it matters, and
only then promoted.

## Lifecycle

| Status | Meaning |
|---|---|
| `idea` | Captured, not examined. No effort spent yet. |
| `exploring` | Being researched or discussed. Open questions listed. |
| `decided` | Promoted to an ADR, BDR, or OpenSpec change. Link it. |
| `parked` | Deliberately postponed. Reason recorded. |
| `rejected` | Will not be pursued. Reason recorded. |

## Rules

- One file per theme, not per idea (for example `card-and-sync.md`).
- Every entry uses the template below. No entry without a problem statement.
- An entry may link to an ADR/BDR/change, but the decision lives there, not here.
- `decided` entries keep their text; do not rewrite history. Add a link and the
  date.
- Ideas that contradict an accepted ADR must say so explicitly and name the ADR.

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

## Index

| File | Theme | Status |
|---|---|---|
| [prediction-algorithms.md](prediction-algorithms.md) | Prediction inputs, outliers, confidence, ovulation, phases | decided — BDR-0004 |
| [domain-model.md](domain-model.md) | Domain entities, invariants, identity, ports | decided — ADR-0006 |
| [card-and-sync.md](card-and-sync.md) | Lovelace card design and external data copy (Sheets, Drive) | idea |
| [period-logging.md](period-logging.md) | Backdating a period start, closing a specific past period, dedup | idea |
| [parked/](parked/README.md) | Drafted OpenSpec changes that are not active work | parked |

## Order of work

1. **Prediction algorithms** — what the product promises. **Decided** in BDR-0004
   and **implemented** in the `add-cycle-prediction` change.
2. **Domain data model** — entities, invariants, identity, `Clock`, repository
   port. **Decided** in ADR-0006 and **implemented** in
   `custom_components/cycle_tracker/domain/`.
3. **Migrate the coordinator** — the prediction seam is done: the coordinator is
   now an adapter around `build_snapshot`. The remaining use cases (`log_start`,
   `log_end`, persistence) still live in the coordinator.
4. **Persistence port and adapters** — local cache first, then the proposed
   Google Sheets adapter (ADR-0004 stays `proposed` until the model is settled).
5. **Lovelace card** — depends on stable entities; change is parked.
6. **Development tooling** — independent of the product order; the active
   `dev-mcp-tooling` change is unaffected.

The product roadmap in `TempFiles/product_roadmap_ha_cycle_tracker.md` still
describes phases and features. This section records the engineering order, which
is not the same thing.
