# Ideas: Presenting Cycle History

Theme: how cycle history is laid out for reading — row order in the Google Sheet,
and charts of period and cycle lengths over time.

---

### I-014: New rows at the top of the Google Sheet

- **Status:** decided
- **Problem:** when Google Sheets is the source of truth, a new period is appended
  to the bottom of the table (`repository.py:313`), so the most recent cycle
  sinks below a growing block of old rows and scrolls out of view. The user reads
  a history newest-first and asked for new dates to appear at the top. Local
  storage re-sorts rows ascending on save (`repository.py:415`) and read
  (`repository.py:387`), calendar events also sort ascending (`calendar.py:89`),
  and no sensor exposes a history list (`sensor.py:316-340`) — so this complaint
  is specifically about the sheet, not about the domain, the calendar or a card.
- **Idea:** put new period rows at the top of the data area, directly under the
  header, instead of at the end. Two shapes to weigh: (a) insert a row just below
  the header with the new values — what the user asked for; (b) keep appending
  to a raw data tab and expose a newest-first view (second tab, `QUERY`/`SORT`
  formula, or pivot) so the raw append-only data stays intact. (b) is the
  lower-risk option if other tools or formulas rely on stable row indices.
- **Value:** the newest cycle is visible as soon as the sheet opens; checking or
  correcting the last entry no longer means scrolling through the whole history.
- **Constraints / conflicts:** ADR-0004 (Google Sheets as source of truth) was
  accepted on 2026-11-20, while the sheet feature shipped in the archived change
  `google-sheets-source-of-truth` (2026-11-17) — so insert-at-top is a follow-up
  to that shipped adapter. The Sheets `append` call writes at the end
  of the table; insert-at-top needs a different API call and shifts existing row
  indices, which can break formulas, ranges or another writer. The header row
  must stay first. Sorting here is presentation: stored order and the domain
  history stay chronological (ADR-0006). Card and entity ordering are out of
  scope for this entry; I-015 covers the chart.
- **Dependencies:**
  - archived `google-sheets-source-of-truth` (2026-11-17; the change this extends) — known
  - I-008 (invalid sheet rows tab may rely on row numbering) — known
  - ADR-0006 (domain history is chronological) — known
  - ADR-0004 (accepted 2026-11-20; its decision covers the sheet as source of
    truth, not row order) — known
- **Open questions:** insert-at-top or raw append plus a sorted view? Does the
  adapter own the layout at all, or is it the user's sheet? How do existing
  sheets migrate — do existing rows move on first write? Do formulas and ranges
  that point at rows shift correctly? Confirm that card, entity attributes and
  calendar stay unaffected (intended: yes).
- **Decision:** decided on 2026-11-20 after the stakeholder clarified the
  workflow: **row 2 is the current period.** She types a new date there and
  updates that same row (end date, flow, notes) while the period is current;
  when a new period starts, she inserts a blank row above row 2 herself
  (option *i* — one click per cycle, no adapter work for the manual path).
  The sorted-view alternative (option b) is rejected: a formula view is
  read-only and would leave the entry point at the bottom.

  Scope of the change this promotes to:

  - `sheets.py` gains one `insert_row` call using `spreadsheets.batchUpdate`
    with `insertDimension` at row 2.
  - `repository.py` inserts directly below the header only for a **new**
    `period_id`; an existing `period_id` is still updated in place. If row 2 is
    blank, write into it rather than inserting another one.
  - `domain/validation.py` flips the duplicate-`period_id` tie-break to
    "smaller row number wins" — the top row is now the newer one. Without it,
    a duplicate without `updated_at` would resolve to the older row below.
  - `read_all` and `sheet_has_data_rows` skip fully blank rows. This is
    required, not cosmetic: if `insertDimension` succeeds but `update_row`
    fails, the immediate refresh after the write would report the empty row 2
    as an invalid row.
  - `sheet-sync` spec: requirement "Write period start" changes from SHALL
    append a row to SHALL insert a new row directly below the header.
  - No migration of existing sheets: old rows keep their order, new rows go
    above the block. Card, entity attributes, calendar and prediction stay
    unaffected — `validate_period_rows` sorts by `start_date`, so sheet order
    is presentational only.

  Verified in code: `services.py:107-108` requests a refresh immediately after
  `log_start` and after a successful `log_end`, so a HA write is read back from
  the sheet on the same call (`coordinator.py:195`); `log_end` takes
  `self._periods[-1]` from the already sorted list, so reversing the sheet
  order does not change which period it closes.

  Known residual: a manual entry in the sheet followed by a card "Start" with
  the same date, before the next read, can produce two rows with that start —
  `async_log_start` deduplicates only against `self._periods[-1]`. That is I-007,
  not introduced by this decision. ADR-0004 was accepted on 2026-11-20 and
  covers the sheet as source of truth, not row order, so no decision blocks
  this layout choice.

  Formal promotion is pending — link to the OpenSpec change to be added when
  `/opsx-propose` turns this into a change.

---

### I-015: Chart of period lengths and cycle lengths over time

- **Status:** exploring
- **Problem:** the integration exposes only current aggregates — average, σ,
  shortest, longest and the tracked count on the statistics sensor
  (`sensor.py:311-334`) — so the user cannot see the trend or the irregularity
  that drives the prediction, which is exactly what makes a prediction
  trustworthy or not. No numeric sensor carries a `state_class`, so Home
  Assistant's built-in history and statistics tooling has no per-cycle series to
  draw either.
- **Idea:** a chart over the last N cycles of period length and cycle length —
  two series, or two charts — with an option to overlay the mean and the ±1σ
  band the prediction uses. Two implementation shapes to weigh: (a) native
  long-term statistics, exposing cycle length and period length as
  statistics-capable sensors so Home Assistant's statistics card and history
  graph render them without a custom chart; (b) a chart in the Lovelace card
  (that change shipped — archived 2026-11-19 — so this would extend it). The
  native-statistics path is the lower-effort one
  and needs no new frontend dependency, but it draws a step series rather than
  one point per cycle.

  Working choice (2026-11-20): a **separate chart card** (revives I-019), not a
  denser section on the daily card and not only native statistics. The daily
  card stays lean and dependency-free; only the chart card would carry a
  charting dependency. Additional libraries are acceptable for charts, but
  each must be justified: small, maintained, with a clean security record, no
  CDN pull and no build step where a vendored file can serve. Try a tiny
  hand-rolled SVG first and add a library only when it earns its place — the
  user would rather not drag a dependency in every time, and would rather stop
  developing once the product is good enough.
- **Value:** users can see whether their cycles are regular and whether a
  prediction is plausible; the chart supports the "window, not a date" promise
  of BDR-0004 instead of hiding it behind a single number.
- **Constraints / conflicts:** the card change shipped (archived 2026-11-19),
  consistent with BDR-0002, so a card chart would extend shipped work.
  Home Assistant collects long-term statistics only for numeric sensors with a
  valid `state_class` (`measurement`, `total`, `total_increasing`), and it
  aggregates hourly min/max/mean from the sensor's current state — so a
  per-cycle value would be sampled many times inside one cycle and the chart
  would show a step series, not one point per cycle. No sensor declares a
  `state_class` today; the statistics sensor's value is the count of tracked
  periods (`sensor.py:311-314`). Sample length ties to I-013. Out-of-range
  cycles are excluded from prediction but stay in history (BDR-0004), so the
  chart has to decide whether to plot them, and the sample window must not
  silently disagree with the prediction window. The chart reads the snapshot,
  not the sheet layout, so it is independent of I-014.

  Two findings from exploring this entry (2026-11-20): the per-cycle series
  does not exist on `Snapshot` today — `History.cycles` and `History.in_range`
  hold cycle lengths, but `build_snapshot` does not carry them forward, and
  `_completed_period_lengths` discards period lengths after computing averages
  — so a domain seam is needed before any chart can render. Also
  `docs/design/card-brief.md` lists "Charts or history views" as a non-goal
  and requires no external assets or CDN; a separate chart card needs that
  brief revisited, not silently ignored.
- **Dependencies:**
  - BDR-0004 (window, uncertainty and outlier rules) — known
  - BDR-0002 (the card ships with the integration) — known
  - `add-lovelace-card` (archived 2026-11-19) — known
  - I-019 (separate statistics card; reopened 2026-11-20 as the surface for
    this chart) — known
  - I-013 (configurable window size; whether the chart shows the prediction
    window or all history, and therefore whether it needs the same setting, is
    not decided) — dependency unknown
- **Open questions:** native statistics, a card chart, or both? How many cycles
  shown — all history or the prediction window? Plot out-of-range cycles with a
  marker instead of dropping them? Include the mean and the ±1σ band? Which
  entity carries the chart data, and when does a per-period value update?
  Which charting library, if any, clears the small-and-safe bar?
- **Decision:** working choice on 2026-11-20: separate chart card, reviving
  I-019, with a small vetted dependency only if hand-rolled SVG is not enough.
  Not yet promoted to an ADR, BDR or OpenSpec change.
