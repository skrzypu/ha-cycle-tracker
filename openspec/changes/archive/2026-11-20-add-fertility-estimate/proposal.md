# Proposal

## Why

Users ask directly whether a given day is suitable for unprotected sex, but the
product currently only shows the fertile window and a confidence value and
leaves the interpretation to them. BDR-0004 (refined 2026-11-19, I-009) decided
to answer this with a raw fertility estimate plus its uncertainty — never a
contraceptive promise — exposed as an opt-in feature so the product promise is
unchanged for everyone who does not enable it.

## What Changes

- Add a pure domain function that computes a fertility estimate from the
  existing prediction and statistics: the six-day fertile window stays as is; an
  extended band adds `margin = max(2, ceil(sigma))` on each side, using the same
  population σ that already feeds period uncertainty and confidence. Below two
  usable cycles the estimate is `unknown`. It takes a reference date and never
  reads the system clock (ADR-0001/0005/0006).
- Add a new, separate entity `fertility_estimate` (not an attribute on existing
  sensors). Its technical state is `outside_estimated_fertile_window`,
  `within_estimated_fertile_window`, or `unknown`, surfaced via `translation_key`
  so copy lives in translations. Attributes: estimated fertile window, margin
  band, `margin_days`, `confidence`, `confidence_band`, `usable_cycle_count`.
- Add an opt-in config-entry option `enable_fertility_estimate` (default
  `False`) in the options flow only, resolved through the existing
  options → data → default `_setting` resolver with no migration. When disabled
  the entity is not created at all. Changing options reloads the entry.
- Add factual UI copy (PL): „poza szacowanym oknem płodnym" / „w szacowanym
  oknie płodnym" / „brak danych", with uncertainty in the same frame as the
  fact and the symmetric disclaimer from BDR-0004. The word ban (no
  „bezpieczny", „dni bezpieczne", „możesz", „ryzyko zajścia") applies to all new
  copy.
- Add a conditional fertility section to the shipped Lovelace card, rendered
  only when the `fertility_estimate` entity exists, so no empty block appears.

## Capabilities

### New Capabilities

- `fertility-estimate`: an opt-in, uncertainty-aware fertility estimate derived
  from the existing prediction and population σ — its computation, its
  dedicated entity and technical states, its default-off configuration, and its
  factual, non-contraceptive presentation on the card.

### Modified Capabilities

- None. The `cycle-prediction` spec is not changed: the six-day fertile window,
  two-cycle minimum, confidence formula, and the "estimate, not a contraceptive
  guarantee" wording all stay as they are. This change only presents the
  existing window's uncertainty in an optional, separate entity.

## Impact

- Code: `const.py` (new option/default/attributes), `config_flow.py` (`_setting`
  defaults and options-flow toggle), `coordinator.py` (setting + snapshot data),
  a new domain module for the estimate and a `FertilityEstimate` model, a new
  sensor entity, `translations/en.json` and `pl.json` (state copy + disclaimer),
  and the card (`cycle-tracker-card.js`) plus its entity-tracking maps.
- Compatibility: additive and default-off. Existing config entries resolve the
  new option to `False` through `_setting`, so no migration is needed and their
  promise and entity set are unchanged.
- Compliance: all new copy must avoid contraceptive-guarantee wording and keep
  the symmetric disclaimer; this is presentation of an estimate, not a new
  method or promise.
