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
