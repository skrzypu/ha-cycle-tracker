# Ideas: Internationalization (i18n)

Theme: in which languages the integration speaks — the Lovelace card, the config
flow, and anything else with user-facing text — and how translations are loaded
and kept consistent.

---

### I-010: Internationalization (i18n): card and config flow in more languages

- **Status:** idea
- **Problem:** the integration has no consistent language story. The v1 card
  ships Polish-only hardcoded labels, while the config flow has text only in
  English (`strings.json` plus `translations/en.json`), so a Polish user gets an
  English setup wizard and a Polish card, and no other user gets anything but
  English during setup and Polish on the dashboard.
- **Idea:** make the card's labels translatable and add a Polish config-flow
  translation (`translations/pl.json`) next to the existing English one, so the
  integration supports Polish and English consistently, with more languages
  added later. Follow Home Assistant frontend localization conventions for the
  card so language switching works the same way as in core frontend.
- **Value:** one language across setup and daily card instead of a mix; a broader
  audience without forking the card; matches the Polish-first product direction
  while removing the English-only setup step for Polish users.
- **Constraints / conflicts:** the parked card design
  (`docs/ideas/parked/add-lovelace-card/design.md`) lists localization as a
  non-goal and says "the first version uses English strings inline"; current
  direction is instead a Polish-only v1 card with i18n deferred. This idea
  reverses that non-goal for the card. Effort grows with every language and every
  string change, and card text has no build step, so whatever mechanism is chosen
  must work from a single-file card. How a card served by an integration loads
  Home Assistant translations is unverified.
- **Dependencies:**
  - `docs/ideas/parked/add-lovelace-card/` (the card; parked change draft, not an
    active OpenSpec change — confirmed to exist) — known
  - `custom_components/cycle_tracker/translations/` (config-flow translations;
    only `en.json` exists today) — known
  - Home Assistant frontend mechanism for localizing a custom card
    (`localize()`/`hass.localize` vs bundled strings) — dependency unknown
    (unconfirmed: the exact loading path for a card served by an integration was
    not checked)
- **Open questions:** which localization mechanism for the card (HA frontend
  `localize()` vs strings bundled in the card file)? Scope — card only, or
  integration-wide including services, entities, and diagnostics? Which languages
  after Polish and English, and who maintains them?
- **Decision:** —
