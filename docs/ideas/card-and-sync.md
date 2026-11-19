# Ideas: Card Design and External Data Copy

Theme: how the Lovelace card looks and behaves, and whether cycle data should
also live outside Home Assistant.

Status as of 2026-11-19. The card itself shipped via the `add-lovelace-card`
change (archived 2026-11-19 at
`openspec/changes/archive/2026-11-19-add-lovelace-card/`); the entries below are
the design and product questions around it.

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
  keyboard operable, and work without external assets. OpenDesign is now
  available through its Docker/MCP workshop (ADR-0007); the card prototype was
  updated to the three-headline layout in the `add-lovelace-card` change.
- **Dependencies:**
  - `add-lovelace-card` (archived 2026-11-19; card prototype and design) — known
  - `docs/design/card-brief.md` (the design brief this idea asks for) — known
- **Open questions:** what is the single most important number on the card?
  Should the actions dominate or the prediction? Does the user want a compact
  row for a dashboard or a larger tile?
- **Decision:** —

### I-002: Google Sheets as a one-way copy of cycle data

- **Status:** decided
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
- **Dependencies:**
  - ADR-0001 (local-only; contradicted and narrowed by this decision) — known
  - ADR-0004 (Google Sheets as source of truth) — known
  - BDR-0003 (cycle data in the user's own Sheet) — known
- **Open questions:** which auth model (service account vs OAuth refresh token
  vs Apps Script webhook)? Which columns and granularity? Append-only log or
  one row per period? What happens when the network is down?
- **Decision:** decided differently on 2026-11-09: the sheet is canonical, not a
  copy. See [ADR-0004](../adr/0004-google-sheets-source-of-truth.md) and
  [BDR-0003](../bdr/0003-cycle-data-user-google-sheet.md); implementation in the
  `google-sheets-source-of-truth` change, archived 2026-11-17 at
  `openspec/changes/archive/2026-11-17-google-sheets-source-of-truth/`.

### I-003: Two-way sync with a Google Sheet

- **Status:** decided
- **Problem:** the user might prefer editing history in a spreadsheet rather
  than in Home Assistant.
- **Idea:** edits in the Sheet change Home Assistant data.
- **Value:** bulk editing and migration from an existing spreadsheet.
- **Constraints / conflicts:** same ADR-0001 conflict as I-002, plus conflict
  resolution, deletion semantics, and polling or webhook infrastructure. Much
  larger than I-002.
- **Dependencies:**
  - ADR-0004 (single store / source of truth) — known
  - `google-sheets-source-of-truth` (archived 2026-11-17; single-store read/write) — known
- **Open questions:** who wins on conflict? How are deletions represented? Is
  polling every N minutes acceptable?
- **Decision:** resolved on 2026-11-09 by treating the sheet as the single store
  rather than syncing two stores: Home Assistant reads and writes the sheet
  directly, last-write-wins per row. See
  [ADR-0004](../adr/0004-google-sheets-source-of-truth.md). Implemented in the
  `google-sheets-source-of-truth` change, archived 2026-11-17.

### I-004: Encrypted Google Drive backup

- **Status:** parked
- **Problem:** roadmap Phase 3 asks for an encrypted backup to Google Drive.
- **Idea:** scheduled encrypted `.json`/`.csv` export to a Drive folder.
- **Value:** disaster recovery without exposing plaintext cycle data.
- **Constraints / conflicts:** same ADR-0001 conflict; encryption key management
  is the hard part.
- **Dependencies:**
  - ADR-0001 (local-only; would need narrowing for a cloud backup) — known
  - I-002 (the one-way copy decision this follows) — known
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
- **Dependencies:**
  - `add-lovelace-card` (archived 2026-11-19; the card this would extend) — known
- **Open questions:** is one tap more important than the extra field?
- **Decision:** parked; the service keeps the field, the card can add it later.

### I-006: A "period is open" entity

- **Status:** decided
- **Problem:** the card cannot tell whether a period is currently open, so the
  end action relies on the service rejecting the call.
- **Idea:** expose a binary sensor or an attribute that says a period is open.
- **Value:** the card can disable the end action honestly, and automations get a
  clean signal.
- **Constraints / conflicts:** adds an entity and a coordinator change; touches
  the `cycle-tracking` spec.
- **Dependencies:**
  - `add-lovelace-card` (archived 2026-11-19; shipped the binary sensor) — known
- **Open questions:** binary sensor vs attribute on an existing sensor? Does it
  belong in the card change or a separate one?
- **Decision:** implemented as the period-open binary sensor in
  `custom_components/cycle_tracker/binary_sensor.py`, shipped in the
  `add-lovelace-card` change, archived 2026-11-19.

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
- **Constraints / conflicts:** extends the archived `google-sheets-source-of-truth`
  design decisions 8 and 9 (exclude-and-report, repair issues); builds on the
  warning value object from ADR-0006; fixing from Home Assistant is I-007.
- **Dependencies:**
  - BDR-0003 (the sheet is canonical) — known
  - ADR-0004 (Google Sheets source of truth) — known
  - ADR-0006 (warning value object) — known
  - archived `google-sheets-source-of-truth` design (2026-11-17), decisions 8–9 — known
  - I-007 (the fix side) — known
  - `add-lovelace-card` (archived 2026-11-19; the UI surface) — known
- **Open questions:** a Lovelace tab or a card section? Can the row be fixed in
  Home Assistant directly (does I-008 need I-007, or can it stand alone)? Does
  it also show rows dropped for extra columns? Does the shipped card need a
  dedicated section for rejected rows?
- **Decision:** —

### I-011: Several people in one home — entity naming, card binding, dashboards

- **Status:** idea
- **Problem:** the integration supports several config entries (one Google Sheet
  per person), which is the natural model for a household with more than one
  menstruating person. The card side has caught up: it binds to a device through
  the entity registry and the bundled dashboard seeds one bound card per device,
  shipped in the `add-lovelace-card` change (archived 2026-11-19). What remains
  is entity naming — IDs do not come from `has_entity_name` with a per-entry
  device name, so they still depend on how a device was created or renamed (an
  area prefix was observed on a first live install).
- **Idea:** make the integration own its entity IDs: adopt `has_entity_name` with
  a per-entry device name so the ID no longer depends on how a device was
  created or renamed, and define a migration story for existing IDs. I-010
  covers the `translation_key`/entity-name side of the same change.
- **Value:** stable, predictable entity IDs per person; the shipped device
  binding and per-device dashboard cards keep working across renames and new
  entries.
- **Constraints / conflicts:** renaming existing entities would break user
  automations, so any naming scheme change needs a migration story; the area
  prefix observed in the wild is not produced by the integration's code, so the
  scheme must tolerate legacy IDs. I-010 overlaps on `has_entity_name` and
  entity names.
- **Dependencies:**
  - `add-lovelace-card` (archived 2026-11-19; device binding and bundled dashboard) — known
  - I-010 (i18n; overlaps on `has_entity_name` and entity names) — known
  - a decision record for entity naming and multi-entry UI — dependency unknown (no such record exists yet)
  - whether Home Assistant added the prefix (device/area creation) or the entities were renamed — dependency unknown
- **Open questions:** should the integration adopt `has_entity_name` and a
  per-entry device name, and how do existing IDs migrate? Does the I-010 overlap
  need one shared decision record? What caused the observed area prefix?
- **Decision:** —
