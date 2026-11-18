# Design

## Context

See `proposal.md` for the motivation. The constraints that shape this design:

- **BDR-0004** fixes the product rules (windows, minimum history, outliers,
  gaps, confidence, late state, phase priority).
- **ADR-0005** requires the domain to be pure Python: no Home Assistant imports,
  prediction strategies behind a substitution boundary, dependencies injected.
- **ADR-0006** fixes the entity shape: `Period` is the only stored entity,
  `Cycle` and `Prediction` are derived on read, `Clock` is a port.
- **Current code.** `prediction.py` holds two strategies. `coordinator.py`
  derives cycle lengths, statistics, cycle day and phases, and reads
  `date.today()` nowhere directly — entities do. `sensor.py` recomputes
  ovulation from the configured length and hard-codes confidence `0.5`.
  `calendar.py` projects twelve periods from the configured length.
- **No `tests/` directory exists**, and `requirements-dev.txt` pins
  `pytest-homeassistant-custom-component==0.13.305` (Home Assistant 2026.1.0,
  CPython 3.13). Any entity-level test needs that baseline; domain tests must
  not.
- **No `pyproject.toml`**, so pytest has no configured asyncio mode or test
  paths yet.

## Goals / Non-Goals

**Goals:**

- One pure function that turns periods, configuration and a reference date into
  a `Prediction`, used by every entity.
- Strategy selection that is open for extension without editing the pipeline.
- Domain tests that run without Home Assistant, including an import-boundary
  check.
- Entity contracts in `sensor.py` and `calendar.py` that expose the prediction
  instead of recomputing it.
- A calculation path that is deterministic and trivially testable with a fixed
  reference date.

**Non-Goals:**

- Migrating storage to `Period` records with persistent `period_id`; that stays
  with the coordinator/use-case migration in ADR-0006's follow-up.
- Home Assistant event-bus events, late notifications, options-flow outlier
  bounds, the Lovelace card, and Google Sheets.
- Repair issues for data warnings; this change exposes them as attributes.
- Changing how periods are logged beyond what prediction reads.

## Decisions

### 1. A `domain` subpackage inside the integration

`custom_components/cycle_tracker/domain/` with:

```
domain/
  models.py       Period, Cycle, Prediction, DataWarning, ConfidenceBand, CyclePhase
  history.py      usable cycles, filters, warnings, window selection
  strategies.py   PredictionStrategy protocol + mean / wma / median + registry
  statistics.py   CycleStatistics from the same usable window
  prediction.py   predict() pipeline, windows, late state
  events.py       project_events() for the calendar
  ports.py        Clock, PeriodRepository (Protocol)
```

Alternatives considered: keep everything in `prediction.py` (violates ADR-0005,
mixes filtering/statistics/events in one file); a top-level `domain/` package
outside the integration (Home Assistant's loader expects everything under the
component, and HACS ships the component directory only).

### 2. `predict()` returns `Prediction | None`

```python
@dataclass(frozen=True)
class PredictionConfig:
    period_length: int
    cycle_length: int  # used only for the single-cycle statistics fallback
    outlier_min_days: int = 15
    outlier_max_days: int = 90
    gap_days: int = 90


def predict(
    periods: Sequence[Period],
    config: PredictionConfig,
    strategy_name: str,
    today: date,
) -> Prediction | None: ...
```

`None` is the domain's "unknown" and the adapter maps it to the entity state.
Alternatives: raising an exception (turns absence into control flow in every
caller) or a nullable-field `Prediction` (every consumer re-checks individual
fields; `None` states the truth once).

### 3. One derived `History`, shared by prediction and statistics

`history.py` produces `(cycles, usable_cycles, warnings)` in one pass:

1. Derive cycles from consecutive starts, oldest first.
2. Drop cycles outside the bounds, recording `DataWarning("outlier", period_id)`.
3. Find the most recent gap longer than 90 days, record `DataWarning("gap",
   period_id)` for the period at that boundary, and discard every cycle at or
   before it.
4. Take the last six of what remains.

Both `predict()` and `statistics()` consume the same `History`, so σ, mean, n
and warnings cannot disagree. Alternatives: recomputing per consumer (today's
bug — three sources of truth); caching it in storage (forbidden by ADR-0006).

Note: step 3 means a long gap also truncates the statistics window for cycle
lengths, while `total_cycles_tracked` and period-length statistics still see the
whole history. That is intended: after a long break the old cycles no longer
describe the present.

### 4. Strategies are a protocol plus a registry

```python
class PredictionStrategy(Protocol):
    def __call__(self, lengths: Sequence[int]) -> int: ...


STRATEGIES = {"arithmetic_mean": ..., "weighted_moving_average": ..., "median": ...}
```

Unknown names fall back to the default with a warning log rather than raising at
runtime; the config flow still validates the choice. Alternatives: an `if/elif`
chain in `get_algorithm` (current code, violates open/closed); a strategy class
per algorithm (no state to carry, so a callable is enough).

All strategies return whole days through a shared `round_half_up()` helper, so
`28.5` becomes `29` independently of Python's banker's rounding.

### 5. Windows are computed from the usable set, not from the forecast

- `sigma = pstdev(usable_lengths)` — the usable cycles are the whole set being
  described, so population deviation avoids inflating small samples. Verified
  against `statistics.pstdev`.
- `uncertainty_half_width = max(2, ceil(sigma))` — the floor applies even at
  σ = 0, so a two-cycle history never looks more certain than it is.
- `ovulation_center = next_period - 14 days`;
  `ovulation = center ± 2`; `fertile = [center - 5, center]`.
- `confidence = min(1, 1 - sigma / mean) * min(1, n / 6)`, computed from the
  usable set. It therefore describes the data, not the chosen strategy; the
  distinction must be documented rather than silently assumed.

All windows are computed from dates, then converted to cycle days only for
phases. Windows that would start before the current cycle start are clamped to
the cycle start.

### 6. Phases come from the ovulation center of the cycle a date belongs to

For a date, find the cycle containing it (last start ≤ date). Its next start is
the next recorded start for a completed cycle, or the predicted next period for
the current cycle. Then:

```
ov_center = next_start - 14 days
ov_start  = max(ov_center - 2, cycle_start + period_length)
ov_end    = min(ov_center + 2, next_start - 1)

cycle_day <= period_length  -> menstrual      # configuration wins
cycle_day <  ov_start       -> follicular
cycle_day <= ov_end         -> ovulatory
else                        -> luteal
```

Using the actual next start for completed cycles makes historical phases stable
once a cycle closes; only the current cycle moves when the prediction moves.
When `ov_start > ov_end` no ovulatory phase exists and the day after the period
is luteal. Alternatives: always using the current prediction for every date
(makes past phases drift); always using the configured length (the current
behavior, contradicts BDR-0004).

### 7. Late state is a property of the prediction, not a shifted date

`is_late = today > next_period`; `days_late = max(0, (today - next_period).days)`.
The predicted date never moves. Days-until-period is
`max(0, (next_period - today).days)`, so it reads 0 both on the due date and
when late, and the late flag carries the distinction.

### 8. Calendar events are projected from the prediction

`project_events(prediction, config, cycles=12, today)` steps forward by the
predicted length and returns domain events (`PERIOD`, `OVULATION`, `FERTILE`).
The calendar adapter maps them to `CalendarEvent`; recorded periods keep being
mapped from history. The uncertainty window stays an attribute, not an event —
it would double the calendar without adding an actionable day.

### 9. Reference date and caching live in the adapter

`prediction.py` never calls `date.today()`. The coordinator implements `Clock`
with `homeassistant.util.dt.now().date()` (local timezone) and caches the derived
snapshot keyed by that date, so a late flag flips at midnight without a new
timer and without recomputing on every attribute read. Alternatives: a
midnight-triggered refresh (extra scheduling surface) and recomputing per entity
property (wasteful and inconsistent across entities).

### 10. Legacy period dictionaries are adapted, not migrated

`Period` needs an id, but stored rows are still `{start_date, end_date,
flow_intensity}`. Until the logging use case writes `period_id`, the adapter
derives a stable id with `uuid.uuid5(NAMESPACE, start_date)` so warnings and
phase lookups have identity across restarts. Storage format and
`STORAGE_VERSION` are unchanged by this change. Alternatives: migrating storage
now (expands scope into the persistence seam ADR-0006 scheduled later);
ephemeral ids (warnings would point at nothing stable).

### 11. `total_cycles_tracked` counts recorded periods

The existing `cycle-tracking` scenario pins one recorded period to a tracked
count of one, which only a period count satisfies. The current code returns
`len(periods) - 1` once two periods exist, so it contradicts its own spec. This
change makes the attribute the number of recorded periods, open one included.

### 12. Test layout and the domain boundary check

```
tests/domain/        pure pytest, no Home Assistant imports
tests/adapters/      pytest-homeassistant-custom-component, fixed clock
tests/imports/       AST check that domain/ imports no HA, aiohttp, voluptuous
```

`pytest.ini` (or a `[tool.pytest.ini_options]` section) sets
`asyncio_mode = auto` and `testpaths = tests`; pre-commit gains a pytest hook.
The import check is an AST walk over `domain/` — cheaper and more precise than a
runtime import guard.

## Risks / Trade-offs

- **[Entity contract breaks automations]** — `days_until_period` stops clamping,
  prediction entities become `unknown` below two usable cycles, and new
  attributes appear. Mitigation: README table update, release note, and keep the
  existing `above: 0, below: 1` automation pattern working.
- **[Users lose history if legacy storage is discarded]** — ADR-0006 decides
  there is no migration. This design deliberately does not discard anything:
  storage is untouched and legacy rows are adapted in memory. Risk deferred to
  the persistence change, where it must be revisited.
- **[Phase changes retroactively]** — mitigated by using the actual next start
  for completed cycles; only the current cycle's phases follow the prediction.
- **[Small-sample σ]** — two cycles give a flattering σ; the ±2-day floor and the
  `n/6` confidence factor are the mitigation.
- **[Late flag flips at midnight]** — mitigated by caching keyed on the local
  date rather than by the six-hour refresh interval.
- **[Import boundary erodes]** — mitigated by the AST check in tests, run by
  pre-commit.
- **[First tests expose unrelated breakage]** — scope the new test run to
  `tests/domain` and `tests/adapters`; do not fix unrelated failures inside this
  change.

## Migration Plan

1. Add the domain package and its tests; nothing imports it yet.
2. Wire `prediction.py` at the integration root to re-export the domain pipeline
   (or delete it and update imports) so there is one implementation.
3. Switch `sensor.py` and `calendar.py` to the coordinator's prediction
   snapshot; delete the duplicated phase, ovulation and statistics arithmetic
   from the adapter layer.
4. Update README entity tables and `docs/guide/algorithms.md` only where the
   shipped contract changed.
5. Rollback is a revert: no storage format changed, so no data migration is
   needed in either direction.

## Open Questions

- Whether statistics should also show an all-history average next to the
  windowed one (BDR-0004 open item). It adds an attribute, not a rule.
- The exact fertile-window wording that avoids reading as contraception (BDR-0004
  defers it to the card). The spec only requires that it is described as an
  estimate.
