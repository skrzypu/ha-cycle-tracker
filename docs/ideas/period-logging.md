# Period Logging

How periods get entered and corrected. Related: [card-and-sync.md](card-and-sync.md)
for the card UI, [domain-model.md](domain-model.md) for period identity.

### I-007: Backdate a period start and close a specific past period

- **Status:** idea
- **Problem:** `cycle_tracker.log_start` accepts any date, but a backdated
  period is stored as one day long (`end_date = start_date`) and `log_end`
  closes only the latest entry. Duplicate detection compares against the last
  period only. Backfilling history from another tracker therefore requires
  logging every cycle chronologically and a mistyped date cannot be corrected
  or closed afterwards. The narrow `end < start` case is already fixed:
  `log_end` now rejects an end date before the start, shipped in the
  `fix-logging-services` change (archived 2026-11-16).
- **Idea:** make backdating a first-class case — let one call record a start
  with an optional end date, or let `log_end` target a specific period by
  `period_id` instead of "the latest open one". Deduplicate against the whole
  stored history, not just the last row, and keep the `end_date < start_date`
  rejection (already shipped in `fix-logging-services`, archived 2026-11-16).
- **Value:** users migrating from another cycle app can import past cycles in
  one pass, and predictions/statistics work immediately instead of after
  several months of logging. Also removes the silent duplicate-row trap.
- **Constraints / conflicts:** ADR-0006 already plans `period_id` as identity;
  stored rows still omit it. Services are a documented public contract
  (ADR-0010), so changes must stay backward compatible. A card now ships
  (`add-lovelace-card`, archived 2026-11-19), but backdating still has no
  dedicated UI.
- **Dependencies:**
  - ADR-0006 (`period_id` identity) — known
  - ADR-0010 (services are a documented public contract) — known
  - `fix-logging-services` (archived 2026-11-16; `end < start` rejection) — known
- **Open questions:** one service call with optional `end_date` versus keeping
  `log_start`/`log_end` separate; what to do with overlapping or duplicate
  starts; whether future dates should be rejected; how rows without
  `period_id` get one on read.
- **Decision:** none.
