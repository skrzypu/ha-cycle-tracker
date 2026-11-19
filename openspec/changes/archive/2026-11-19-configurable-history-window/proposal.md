# Proposal

## Why

The prediction and the displayed cycle-length statistics are limited to the last
six usable completed cycles, fixed by BDR-0004 and the shipped specs and guide.
A user with a long history asked for twelve: six under-samples her real cycles,
so a single old cycle dropping out makes the values jump. The code already has a
`PredictionConfig.history_window` field (default 6) that the coordinator never
sets and the config flow never asks for, and its confidence formula already
divides by that field. The product decision I-013 (decided 2026-11-19, recorded
as an amendment to BDR-0004) resolves the window question; this change applies
it to the settings, the domain wording, the statistics sensor and the card.

## What Changes

- Introduce ONE shared, user-configurable history window N (range 6–24, integer)
  that feeds both prediction and cycle-length statistics. There are no separate
  windows and no service to change it: the setting lives in the config entry and
  is edited through the options dialog only (ADR-0011).
- New config entries store 12 in `entry.data` at setup. Existing entries have no
  stored value and resolve `DEFAULT_HISTORY_WINDOW = 6` through the config-entry
  resolver (options → data → default). No migration and no "created before"
  branching; the option overrides the setup value when present.
- Add `CONF_HISTORY_WINDOW` and a new-entry default constant, a coordinator
  getter using the existing `_setting()` resolver, and a `NumberSelector`
  (min 6, max 24, step 1) in the initial config flow's preferences step
  (alongside the algorithm) and in the options flow.
- Generalize the confidence formula `min(1, 1−σ/mean) × min(1, n/N)` in prose and
  docstrings. The implementation already tracks N via
  `target=config.history_window` in `domain/statistics.py` and
  `domain/prediction.py`, so the formula and the confidence bands (low < 0.4,
  medium 0.4–0.7, high > 0.7) are unchanged.
- Keep the rules that are not being decided: two usable cycles minimum,
  filter-before-window, and gap-truncates-window. "At most six" becomes "at most
  N". The floor of 6 is a lower bound on the SETTING and a cap on cycles used,
  not a data requirement — a user with 2–5 usable cycles still gets a prediction.
- Keep the windowed average cycle length on the statistics sensor and add ONE
  lifetime cycle-length average computed from all in-range cycles in recorded
  history: outliers (outside 15–90 days) excluded, cycles before the most recent
  long gap included. This settles the old conflicting wording in favour of
  exclusion; it is one extra statistic, not a chart and not a second window.
- Render both averages as two labelled rows in the EXISTING statistics section
  of `www/cycle-tracker-card.js` `_renderStatistics`, with the new attribute and
  EN/PL label strings. No separate card (I-019 is parked) and no charts (I-015).
- No breaking changes to entities, services, storage shape or prediction
  algorithms. Existing entries keep an effective window of 6 until the user
  chooses a different value.

## Capabilities

### New Capabilities

None. The change generalizes behavior already owned by existing capabilities
and adds one statistic to an existing sensor and card section.

### Modified Capabilities

- `cycle-prediction`: the window requirement selects at most N usable cycles
  instead of six, and the confidence requirement divides by N instead of the
  literal 6; the two-cycle minimum and filter/gap order are unchanged.
- `cycle-configuration`: adds the shared history-window setting (range 6–24) to
  the config entry, its resolver-backed getter and both the setup and options
  forms.
- `cycle-tracking`: the statistics sensor gains a lifetime cycle-length average
  alongside the windowed average and states that in-range history excludes
  outliers but includes cycles before the most recent gap.
- `lovelace-card`: the collapsible statistics section shows both cycle-length
  averages as labelled rows on the existing card.

## Impact

- **Code**: `domain/ports.py` (setting field/default wording), `domain/history.py`,
  `domain/statistics.py` (lifetime average + docstrings), `domain/prediction.py`
  (docstrings/config wiring), `coordinator.py` (getter + prediction config),
  `config_flow.py` and `const.py` (new key, default, selectors), `sensor.py`
  (new attribute), `www/cycle-tracker-card.js` (two rows).
- **Strings/docs**: `strings.json`, `translations/en.json`, `translations/pl.json`,
  `docs/guide/algorithms.md`, and the archived decision records are NOT edited —
  BDR-0004 already carries the 2026-11-19 amendment (I-013 is decided).
- **Specs**: delta specs for the four modified capabilities above; downstream
  spec files under `openspec/specs/` are updated when the change is applied.
- **Tests**: domain tests (`tests/domain/`) and adapter tests (`tests/adapters/`)
  for the configurable window, resolver/getter, selectors, lifetime average and
  attribute exposure; verification gate is `pre-commit run --all-files`
  (ruff, ruff-format, mypy, pytest).
- **Out of scope**: separate statistics card (I-019, parked), charts (I-015),
  any other all-history statistic, and a service to change the window.
