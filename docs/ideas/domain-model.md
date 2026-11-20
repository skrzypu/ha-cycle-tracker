# Idea: Domain Data Model

- **Status:** decided — recorded in [ADR-0006](../adr/0006-domain-model-contract.md) on 2026-11-10
- **Problem:** the domain currently exists only as a list of dictionaries inside
  `coordinator.py`. Fields, invariants, and identity are implicit, so every
  future change — a repository port, Google Sheets, the card, or new metrics —
  has to guess the shape. ADR-0005 requires the domain to be explicit and
  framework-free, which makes the model the first artifact to settle.
- **Idea:** define the domain model before adding any persistence backend or UI:
  entities, value objects, invariants, and the ports that expose them.
- **Value:** one stable shape for storage, services, sensors, and the sheet; a
  domain that can be tested without Home Assistant; no schema churn later.
- **Constraints / conflicts:** ADR-0005 (SOLID, Clean Architecture, dependency
  rule); ADR-0001 was superseded by ADR-0004, accepted on 2026-11-20; the
  sheet schema in the archived `google-sheets-source-of-truth` change
  (`openspec/changes/archive/2026-11-17-google-sheets-source-of-truth/`) must map
  onto the model,
  not the other way round.
- **Dependencies:**
  - ADR-0005 (SOLID, Clean Architecture, dependency rule) — known
  - `prediction-algorithms.md` (source of the model answers) — known
  - ADR-0004 (Google Sheets source of truth; the sheet schema maps onto the model) — known
- **Open questions:** none blocking the model; see the "Open questions" section below.
- **Decision:** recorded in [ADR-0006](../adr/0006-domain-model-contract.md)
  on 2026-11-10; see "Decided so far" below.

## Decided so far

Derived from `prediction-algorithms.md`, which is the source of these answers.

- **Open periods:** exactly one period may be open at a time, with no duration
  limit. `log_end` closes that period.
- **Scope:** the first model contains only what the prediction algorithms need.
  No speculative fields and no generic observation layer until a real use case
  requires it.
- **Period fields:** `id`, `start`, optional `end`, optional `flow`, optional
  `notes`, `updated_at`. No `created_at`, no `source`.
- **Identity:** a UUID generated once at creation, stored as `period_id`. A date
  correction keeps the identity.
- **Flow:** one of `spotting`, `light`, `medium`, `heavy`.
- **Cycle:** never stored. A cycle is a pair of consecutive period starts,
  derived on read.
- **Invariants:** hard errors only for `end < start` and overlapping periods.
  Everything else is a warning. The model never silently repairs data.
- **Time:** calendar dates, not instants. "Today" comes from a `Clock` port;
  nothing calls `date.today()`.
- **Migration:** none. The integration has not shipped usable data, so the old
  `{start_date, end_date}` dictionaries are discarded.
- **Second open period:** `log_start` while a period is open is a hard error. The
  user closes the open period first; the model never invents an end date.
- **Ports:** `PeriodRepository` (read all, upsert, delete) plus `Clock`. The
  algorithm name and the outlier bounds travel as use-case arguments from
  configuration, not as ports.
- **Notes:** any text in the domain; any length limit belongs to the adapter.
- **Duplicate start dates:** identity decides, not the date. An existing
  `period_id` is an update; a new id with an already used start is an overlap
  error.
- **Warnings:** a domain value object — kind (`outlier`, `gap`, `missing_flow`)
  plus the offending period id. The adapter decides whether that becomes a
  repair issue, an attribute, or a log line.

## Model sketch

```python
@dataclass(frozen=True)
class Period:
    id: PeriodId  # UUID, stable for the life of the row
    start: date
    end: date | None = None
    flow: FlowIntensity | None = None
    notes: str | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class Cycle:  # derived, never persisted
    start: date
    length_days: int  # start-to-start
    period: Period


@dataclass(frozen=True)
class Prediction:  # derived, never persisted
    next_period: date
    uncertainty: tuple[date, date]
    ovulation: tuple[date, date]
    fertile: tuple[date, date]
    confidence: float  # 0..1
    confidence_band: str  # low / medium / high
    is_late: bool
    warnings: tuple[DataWarning, ...]
```

## Open questions

None blocking the model. Remaining product gaps live in
`prediction-algorithms.md`: the all-history statistic and the fertile-window
wording.

## Next step

The model is implemented under `custom_components/cycle_tracker/domain/`
(`models.py`, `validation.py`, `prediction.py`, `strategies.py`, `statistics.py`,
`windows.py`, `ports.py` and others), so this artifact is complete. Remaining
product gaps live in `prediction-algorithms.md`: the all-history statistic and
the fertile-window wording. The Google Sheets source-of-truth adapter is
archived as well (`google-sheets-source-of-truth`, 2026-11-17).
