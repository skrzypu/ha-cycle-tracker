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
| [prediction-algorithms.md](prediction-algorithms.md) | Prediction inputs, outliers, confidence, ovulation, phases | decided — BDR-0004 (2026-11-10) |
| [domain-model.md](domain-model.md) | Domain entities, invariants, identity, ports | decided — ADR-0006 (2026-11-10) |
| [card-and-sync.md](card-and-sync.md) | Lovelace card design, external data copy (Sheets, Drive), several people per home | mixed — decided (I-002/003/006), exploring (I-001), parked (I-004/005/019), idea (I-008/011) |
| [period-logging.md](period-logging.md) | Backdating a period start, closing a specific past period, dedup | idea |
| [safe-days.md](safe-days.md) | Safe days for unprotected sex: today's status, upcoming ranges, confidence | decided — BDR-0004 (2026-11-19) |
| [internationalization.md](internationalization.md) | Card and config flow in more languages, translation loading (i18n) | idea |
| [update-cadence.md](update-cadence.md) | Coordinator update cadence: daily instead of sub-hourly polling, manual refresh | idea |
| [prediction-configurability.md](prediction-configurability.md) | Configurable prediction and statistics window (number of cycles used) | decided — I-013 (2026-11-19), BDR-0004 amendment pending |
| [history-presentation.md](history-presentation.md) | Google Sheet row order (newest on top), charts of period and cycle lengths | idea |
| [symptoms-and-observations.md](symptoms-and-observations.md) | Symptoms, basal body temperature and LH tests alongside periods | idea |
| [diagnostics.md](diagnostics.md) | Last refresh, excluded cycles, gaps and data quality | idea |
| [prediction-accuracy.md](prediction-accuracy.md) | Scoring past predictions against actual period starts | idea |
| [parked/](parked/README.md) | Drafted OpenSpec changes kept as historical reference (both now archived) | reference — both drafts archived |

## Order of work

1. **Prediction algorithms** — what the product promises. **Decided** in BDR-0004
   (2026-11-10) and **implemented** in the `add-cycle-prediction` change.
2. **Domain data model** — entities, invariants, identity, `Clock`, repository
   port. **Decided** in ADR-0006 (2026-11-10) and **implemented** in
   `custom_components/cycle_tracker/domain/`.
3. **Migrate the coordinator** — the prediction seam is done: the coordinator is
   now an adapter around `build_snapshot`. The remaining use cases (`log_start`,
   `log_end`, persistence) still live in the coordinator.
4. **Persistence port and adapters** — local cache first, then the Google Sheets
   adapter, which shipped via the `google-sheets-source-of-truth` change
   (archived 2026-11-17); ADR-0004 records the source-of-truth decision.
5. **Lovelace card** — shipped via the `add-lovelace-card` change
   (archived 2026-11-19), with device binding and one bound card per device in
   the bundled dashboard. Remaining work is entity naming (I-011) and card
   i18n (I-010).
6. **Development tooling** — independent of the product order; the active
   `dev-mcp-tooling` change is unaffected.
7. **Configurable history window** — I-013 decided 2026-11-19: one shared
   window (6–24, 12 for new entries, 6 for existing), options only, plus a
   lifetime average from all in-range cycles. The BDR-0004 amendment is
   pending with `@decision-recorder`; implementation follows as a change.
   The separate statistics card is parked as I-019 until I-015 (charts).

The product roadmap in `TempFiles/product_roadmap_ha_cycle_tracker.md` still
describes phases and features. This section records the engineering order, which
is not the same thing.
