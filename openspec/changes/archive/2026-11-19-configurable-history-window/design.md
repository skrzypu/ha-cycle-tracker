# Design

## Context

See `proposal.md` for motivation. The relevant current state is:

- `domain/ports.py` defines `DEFAULT_HISTORY_WINDOW = 6` and
  `PredictionConfig.history_window`; the domain already uses that field for the
  usable window (`domain/history.py`: `usable = in_range[-window:]`) and for the
  confidence denominator (`target=config.history_window` in
  `domain/statistics.py` and `domain/prediction.py`). No formula change is needed.
- `coordinator.py` builds `PredictionConfig(period_length, cycle_length)` only;
  `_setting()` at line 162 already implements options → data → default, and the
  existing entry update listener reloads the entry after options are saved
  (ADR-0011). The snapshot is cached per local date and invalidated on writes.
- `config_flow.py` accumulates setup answers in `self._data` and creates the
  entry in `_create_sheet_entry()`; the options flow reads defaults through its
  own `_setting()` helper. Both use `selector.NumberSelector` with BOX mode.
- `domain/history.py` keeps every derived cycle in `History.cycles` (including
  outliers and cycles before the most recent gap) and only `History.usable` is
  gap-truncated and N-limited. `build_snapshot()` builds that one `History` and
  feeds prediction, statistics and events.
- `sensor.py` exposes statistics as attributes; `www/cycle-tracker-card.js`
  renders statistics rows with inlined Polish labels in `_renderStatistics`.
- Constraints: pure framework-free domain (ADR-0005/0006), config entry as the
  single settings source (ADR-0011), BDR-0004 already amended on 2026-11-19
  (do not re-amend), I-019 parked, I-015 out of scope.

## Goals / Non-Goals

**Goals:**

- One setting, resolved through the config entry, that reaches the existing
  `history_window` field without changing the pure prediction formula.
- A second, lifetime cycle-length statistic derived from the existing `History`
  without introducing a second window or storing derived values.
- Both averages visible in the existing card statistics section and documented
  in the existing guide/spec wording.

**Non-Goals:**

- No service or other write path for the window; no migration or version branch.
- No new sensor entity, no separate card, no chart, no other all-history statistic.
- No change to the two-cycle minimum, filter order, gap truncation, outlier
  bounds, confidence bands, or prediction strategies.

## Decisions

### 1. One key, two distinct defaults, one resolver

Add `CONF_HISTORY_WINDOW = "history_window"` and new-entry bounds/default
constants to `const.py` (`MIN_HISTORY_WINDOW = 6`, `MAX_HISTORY_WINDOW = 24`,
`DEFAULT_HISTORY_WINDOW_NEW_ENTRY = 12`). The name is deliberately distinct from
`domain.ports.DEFAULT_HISTORY_WINDOW = 6`, which stays as the fallback for
existing entries. `coordinator.py` gains `get_history_window()` implemented with
the existing `_setting(CONF_HISTORY_WINDOW, DEFAULT_HISTORY_WINDOW)` (domain
constant, 6), and `get_prediction_config()` adds
`history_window=self.get_history_window()` to the existing two fields. The
options flow defaults use the same `options → data → default` order; the setup
form defaults to 12, so a fresh entry lands in `entry.data` through the existing
`_data.update(user_input)` / `_create_sheet_entry()` path. No code checks entry
creation dates or rewrites stored data.

Alternative rejected: a single constant of 12 used everywhere would silently
change existing entries' behavior and would need a migration; a service would
create a second write path (ADR-0011).

### 2. Reuse the existing window and confidence implementation

Do not touch the selection or confidence algorithms. `build_history()` already
takes at most N post-filter, post-gap cycles, and both confidence call sites
already divide by N. The work is wiring the resolver into `PredictionConfig` and
generalizing the prose/docstrings ("six" → "N", `n/6` → `n/N`) in
`domain/ports.py`, `domain/history.py`, `domain/statistics.py`,
`domain/prediction.py`, `docs/guide/algorithms.md`, and the main specs when the
change is applied. BDR-0004 and I-013 are already decided and are not edited.

Alternative rejected: adding a second window setting or computing confidence
from a literal six would contradict the decision and make the sensor disagree
with the prediction.

### 3. Lifetime average from a second view of the same `History`

Extend the frozen `History` dataclass with `in_range: tuple[Cycle, ...] = ()`,
populated in `build_history()` from the same `_within_bounds()` predicate used
for `usable`, but without the gap truncation or the N slice. `cycles` remains the
full set for warnings; `in_range` is the in-bounds superset; `usable` is its
gap-truncated N-tail. `statistics()` computes `lifetime_average_cycle_length`
with `fmean` over `history.in_range` when it is non-empty, otherwise `None`
(surfaced as unknown). The default keeps any existing direct construction of
`History` valid. No cycle length is persisted and no new domain function needs
to duplicate the outlier-bounds rule.

Alternative rejected: filtering `history.cycles` inside `statistics()` with a
second copy of the bounds check would let the two views drift; exposing a public
filter helper would add API for one caller.

### 4. Expose one attribute and two card rows

Add `ATTR_LIFETIME_AVERAGE_CYCLE_LENGTH = "lifetime_average_cycle_length"` to
`const.py`, a matching field on `CycleStatistics`, and one entry in
`CycleStatisticsSensor.extra_state_attributes` next to
`ATTR_AVERAGE_CYCLE_LENGTH`. In `_renderStatistics`, insert two labelled rows in
the existing `rows` array — the existing windowed average and the new lifetime
average — following the same `formatNumeric(..., 1)` and not-tracked path as the
current rows. Labels stay Polish and inlined like the other card rows; the new
`history_window` field label/help is added to `strings.json`,
`translations/en.json` and `translations/pl.json` under the `preferences` and
`options.init` data keys. No card element, dashboard seed or service changes.

Alternative rejected: a second statistics card (I-019, parked) or a chart
(I-015) would add a seeding decision and a new frontend surface for two values.

## Risks / Trade-offs

- **Opting into a larger window changes confidence and averages** — expected:
  σ grows with more cycles and the denominator becomes N. Mitigation: keep
  bands and formula unchanged, and add scenarios/tests for N=6 vs N=12.
- **A larger window makes predictions less responsive** — accepted trade-off in
  I-013; users choose the balance in the options dialog.
- **Snapshot cached per date** — an options change is followed by the existing
  entry reload. Mitigation: do not add a new propagation path; verify the getter
  is read when the config is rebuilt.
- **`History` gains a field** — low risk; the default value keeps existing
  constructions valid, and no adapter builds it directly.
- **Card has no JS test harness** — mitigation: manual checklist plus the
  existing string/asset tests; backend coverage carries the verification gate.

## Migration Plan

None for data. Existing entries keep resolving to 6 until the user saves a
window; new entries store 12 at setup. Rollback is a revert of the code, forms
and attributes: any saved `history_window` option becomes an unused key and
does not affect older code. No storage write, version bump, or BDR/idea edits.

## Verification

`pre-commit run --all-files` is the gate (ruff, ruff-format, mypy, pytest), with
domain tests for the window/lifetime average and adapter tests for the resolver,
selectors, attribute and card strings.
