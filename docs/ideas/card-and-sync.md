# Ideas: Card Design and External Data Copy

Theme: how the Lovelace card looks and behaves, and whether cycle data should
also live outside Home Assistant.

Status as of 2026-11-09. The card itself is planned in
`openspec/changes/add-lovelace-card/`; the entries below are the open design and
product questions around it.

---

### I-001: Visual direction of the card

- **Status:** exploring
- **Problem:** the roadmap requires a card for one-tap period start/end but says
  nothing about layout, hierarchy, or tone. Without a brief, every mock is a
  guess.
- **Idea:** define a short design brief first (content, states, constraints),
  then produce two or three layout variants and pick one.
- **Value:** fewer rework loops; a card that reads well at a glance on a phone.
- **Constraints / conflicts:** must use Home Assistant theme variables only, be
  keyboard operable, and work without external assets. OpenDesign is not
  installed yet (Docker missing), so the first pass is text plus a static mock.
- **Open questions:** what is the single most important number on the card?
  Should the actions dominate or the prediction? Does the user want a compact
  row for a dashboard or a larger tile?
- **Decision:** —

### I-002: Google Sheets as a one-way copy of cycle data

- **Status:** exploring
- **Problem:** the data lives only inside Home Assistant storage. The user wants
  it visible/analyzable in a spreadsheet, and an off-device copy.
- **Idea:** Home Assistant appends or updates rows in a Google Sheet when a
  period is logged (one-way: HA → Sheet). The Sheet is a copy, never the source
  of truth.
- **Value:** easy charting and sharing with a clinician; a readable backup the
  user controls.
- **Constraints / conflicts:** **contradicts ADR-0001** (local-only, no cloud,
  no external API). Promoting this idea requires superseding or narrowing that
  ADR, plus a new ADR for the mechanism and a BDR for the product promise.
  Sends cycle data to Google. Needs credentials stored in HA.
- **Open questions:** which auth model (service account vs OAuth refresh token
  vs Apps Script webhook)? Which columns and granularity? Append-only log or
  one row per period? What happens when the network is down?
- **Decision:** decided differently on 2026-11-09: the sheet is canonical, not a
  copy. See [ADR-0004](../adr/0004-google-sheets-source-of-truth.md) and
  [BDR-0003](../bdr/0003-cycle-data-user-google-sheet.md); implementation in
  `openspec/changes/google-sheets-source-of-truth/`.

### I-003: Two-way sync with a Google Sheet

- **Status:** parked
- **Problem:** the user might prefer editing history in a spreadsheet rather
  than in Home Assistant.
- **Idea:** edits in the Sheet change Home Assistant data.
- **Value:** bulk editing and migration from an existing spreadsheet.
- **Constraints / conflicts:** same ADR-0001 conflict as I-002, plus conflict
  resolution, deletion semantics, and polling or webhook infrastructure. Much
  larger than I-002.
- **Open questions:** who wins on conflict? How are deletions represented? Is
  polling every N minutes acceptable?
- **Decision:** resolved on 2026-11-09 by treating the sheet as the single store
  rather than syncing two stores: Home Assistant reads and writes the sheet
  directly, last-write-wins per row. See
  [ADR-0004](../adr/0004-google-sheets-source-of-truth.md).

### I-004: Encrypted Google Drive backup

- **Status:** parked
- **Problem:** roadmap Phase 3 asks for an encrypted backup to Google Drive.
- **Idea:** scheduled encrypted `.json`/`.csv` export to a Drive folder.
- **Value:** disaster recovery without exposing plaintext cycle data.
- **Constraints / conflicts:** same ADR-0001 conflict; encryption key management
  is the hard part.
- **Open questions:** where does the key live? Does Home Assistant's own backup
  already cover this?
- **Decision:** parked; revisit after I-002 research.

### I-005: Flow intensity in the card

- **Status:** parked
- **Problem:** `log_start` accepts an optional flow intensity, but the card sends
  only the date.
- **Idea:** a small selector or long-press menu to pick spotting/light/medium/heavy.
- **Value:** richer data without opening Developer Tools.
- **Constraints / conflicts:** adds interaction cost to a "one-tap" card; needs a
  decision on defaults.
- **Open questions:** is one tap more important than the extra field?
- **Decision:** parked; the service keeps the field, the card can add it later.

### I-006: A "period is open" entity

- **Status:** exploring
- **Problem:** the card cannot tell whether a period is currently open, so the
  end action relies on the service rejecting the call.
- **Idea:** expose a binary sensor or an attribute that says a period is open.
- **Value:** the card can disable the end action honestly, and automations get a
  clean signal.
- **Constraints / conflicts:** adds an entity and a coordinator change; touches
  the `cycle-tracking` spec.
- **Open questions:** binary sensor vs attribute on an existing sensor? Does it
  belong in the card change or a separate one?
- **Decision:** —

### I-008: A tab for invalid sheet rows

- **Status:** idea
- **Problem:** manual entries in the sheet can be wrong (a date typo, an end
  before its start, a duplicate id). The project "excludes and reports" them as
  a small repair issue, so the user cannot see clearly which rows are broken and
  why.
- **Idea:** a dedicated place in Home Assistant (a tab, view or card) that lists
  the rejected rows: row/id, value, and reason. It joins up with manual
  correction — in the sheet, or in Home Assistant (I-007).
- **Value:** the user can fix what she mistyped without guessing; a broken row
  does not vanish silently and does not poison predictions.
- **Constraints / conflicts:** extends the parked `google-sheets-source-of-truth`
  design decisions 8 and 9 (exclude-and-report, repair issues); builds on
  `DataWarning` from ADR-0006; fixing from Home Assistant is I-007.
- **Dependencies:**
  - BDR-0003 (the sheet is canonical) — known
  - ADR-0004 (Google Sheets source of truth) — known
  - ADR-0006 (`DataWarning` = "what is wrong") — known
  - parked `google-sheets-source-of-truth` design, decisions 8–9 — known
  - I-007 (the fix side) — dependency unknown (does I-008 require I-007, or
    stand alone?)
  - `add-lovelace-card` (the UI surface) — dependency unknown (the card is
    parked, so the tab's form is undetermined)
- **Open questions:** a Lovelace tab or a card section? Can the row be fixed in
  Home Assistant directly? Does it also show rows dropped for extra columns?
- **Decision:** —

### I-011: Several people in one home — entity naming, card binding, dashboards

- **Status:** idea
- **Problem:** the integration already supports several config entries (one
  Google Sheet per person), which is the natural model for a household with more
  than one menstruating person. The UI surface does not follow: on the first live
  installation the entities were created with an area prefix
  (`sensor.prywatne_cycle_tracker_cycle_day`), so the card's conventional IDs
  (`sensor.cycle_tracker_cycle_day`) matched nothing and every value rendered as
  "brak danych". The card now falls back to a same-domain suffix match, but with
  two entries that fallback is ambiguous, and the bundled dashboard seeds a
  single card with no entity mapping.
- **Idea:** decide entity naming and card binding together: (a) make the
  integration own its entity IDs (for example `has_entity_name` with a
  per-entry device name), so the ID does not depend on how a device was created
  or renamed; (b) let a card bind to an entry or device (an `entry`/`device`
  option resolved through the entity registry) instead of guessing by suffix;
  (c) make the bundled dashboard multi-person aware: one view per entry, or one
  dashboard per entry created from the entry name.
- **Value:** a household can track two or more people without YAML surgery per
  card, and the first installation stops depending on an accidental area prefix.
- **Constraints / conflicts:** the card runs in the frontend and cannot read
  config entries today, so a binding option needs either a companion entity that
  exposes the entry ID or a registry-based lookup in the card; renaming existing
  entities would break user automations, so any naming scheme change needs a
  migration story; the area prefix observed in the wild is not produced by the
  integration's code, so the scheme must tolerate legacy IDs.
- **Dependencies:**
  - `add-lovelace-card` (bundled dashboard, card entity resolution) — known
  - I-010 (i18n: `has_entity_name`, `translation_key`, entity names) — known,
    overlapping: both touch entity naming
  - a decision record for entity naming and multi-entry UI — missing
  - whether Home Assistant added the prefix (device/area creation) or the
    entities were renamed — dependency unknown
- **Open questions:** should the integration adopt `has_entity_name` and a
  per-entry device name, and how do existing IDs migrate? Should the card accept
  an `entry_id`/`device_id` option, or should each person get their own
  dashboard? Does the bundled dashboard stay single-person by design?
- **Decision:** —
