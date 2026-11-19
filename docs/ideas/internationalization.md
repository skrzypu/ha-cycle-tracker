# Ideas: Internationalization (i18n)

Theme: in which languages the integration speaks — the Lovelace card, the config
flow, and anything else with user-facing text — and how translations are loaded
and kept consistent.

---

### I-010: Internationalization (i18n): card and config flow in more languages

- **Status:** idea
- **Problem:** the config flow now speaks both Polish and English
  (`strings.json`, `translations/en.json` and `translations/pl.json`), but the
  shipped v1 card still has Polish-only hardcoded labels and no translatable
  strings. The remaining gap is card i18n: an English or other-language Home
  Assistant instance gets an English setup wizard but a Polish-only card.
- **Idea:** make the card's labels translatable so the integration supports
  Polish and English consistently on the card as it already does in the config
  flow, with more languages added later. Follow Home Assistant frontend
  localization conventions for the card so language switching works the same
  way as in core frontend. The config-flow Polish translation is already done.
- **Value:** one language across setup and daily card instead of a mix; a broader
  audience without forking the card; matches the Polish-first product direction
  while removing the English-only card for non-Polish users.
- **Constraints / conflicts:** the card design
  (`openspec/changes/archive/2026-11-19-add-lovelace-card/design.md`, archived
  2026-11-19) explicitly defers localization beyond Polish — "Card i18n beyond
  Polish ... belongs" to later work — and the shipped v1 card uses Polish
  labels inline. This idea reverses that deferral for the card. Effort grows
  with every language and every string change, and card text has no build step,
  so whatever mechanism is chosen must work from a single-file card. How a card
  served by an integration loads Home Assistant translations is unverified.
- **Dependencies:**
  - `add-lovelace-card` (archived 2026-11-19; the card served by the integration) — known
  - `custom_components/cycle_tracker/translations/` (config-flow translations;
    `en.json` and `pl.json` both exist) — known
  - Home Assistant frontend mechanism for localizing a custom card
    (`localize()`/`hass.localize` vs bundled strings) — dependency unknown
    (unconfirmed: the exact loading path for a card served by an integration was
    not checked)
- **Open questions:** which localization mechanism for the card (HA frontend
  `localize()` vs strings bundled in the card file)? Scope — card only, or
  integration-wide including services, entities, and diagnostics? Which
  languages after Polish and English, and who maintains them?
- **Decision:** —
