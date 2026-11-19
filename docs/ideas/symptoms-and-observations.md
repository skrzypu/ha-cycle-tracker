# Ideas: Symptoms and Observations

Theme: day-level observations recorded alongside periods — symptoms, basal body
temperature and LH tests — and whether they ever feed prediction.

---

### I-016: Log symptoms, basal body temperature and LH tests alongside periods

- **Status:** idea
- **Problem:** the domain stores periods and the cycles derived from them, but no
  day-level observations: the model has `Period`, `Cycle`, `DataWarning`,
  `Prediction` and related value types (`domain/models.py:33-93`), nothing for a
  symptom, a temperature or a test result. The only hint of this need in the
  backlog is flow intensity in the card (I-005). Users who track cycles in a
  fertility app also record symptoms, BBT and LH tests, and without them they
  have to keep a second app and explain an unusual cycle from memory.
- **Idea:** add a per-day observation record — symptom tags, an optional BBT value
  with unit, and an LH test result — stored next to periods, written through a
  service and exposed as entity attributes. Charts (I-015) can plot the series
  later. First pass is data capture only; decide separately whether BBT or LH
  results change the ovulation estimate, which BDR-0004 currently derives from
  the prediction minus 14 days.
- **Value:** users stop duplicating data in another app; irregular cycles get
  context; later, ovulation estimates could be supported by observed data rather
  than a fixed offset.
- **Constraints / conflicts:** this is a domain-model change, not an adapter
  change: ADR-0006 defines the current model contract, and a new entity plus its
  invariants and persistence port are needed. ADR-0001 keeps data local — this
  would be the most sensitive data the integration holds, so no cloud path
  should be introduced by default. If the sheet is ever the source of truth,
  ADR-0004's column layout would need new columns and the parked
  `google-sheets-source-of-truth` change would have to carry them. BDR-0004's
  prediction contract stays untouched until a separate decision is made.
- **Dependencies:**
  - ADR-0006 (explicit domain model contract) — known
  - ADR-0001 (local-only storage and processing) — known
  - ADR-0004 (sheet columns and source-of-truth scope) — dependency unknown
  - parked `google-sheets-source-of-truth` (where sheet columns would land) —
    dependency unknown
  - I-015 (chart of cycle and period lengths; a future place to plot the new
    series) — dependency unknown
  - I-005 (flow intensity in the card) — dependency unknown
- **Open questions:** free-text notes or a fixed symptom taxonomy? One record per
  day or one per event? BBT unit (°C/°F) and import from other apps? Do
  observations only inform the user, or feed prediction — and if they feed it,
  how is that validated? Retention, export and redaction of health data? What
  happens to an observation on a day that later turns out to be a period day?
- **Decision:** —
