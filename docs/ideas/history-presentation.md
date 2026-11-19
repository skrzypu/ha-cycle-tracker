# Ideas: Presenting Cycle History

Theme: how cycle history is laid out for reading — row order in the Google Sheet,
and charts of period and cycle lengths over time.

---

### I-014: New rows at the top of the Google Sheet

- **Status:** idea
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
- **Constraints / conflicts:** ADR-0004 (Google Sheets as source of truth) is
  still `proposed`, and the sheet feature lives in the parked change
  `docs/ideas/parked/google-sheets-source-of-truth/` — so this is a requirement
  on that change, not on shipped code. The Sheets `append` call writes at the end
  of the table; insert-at-top needs a different API call and shifts existing row
  indices, which can break formulas, ranges or another writer. The header row
  must stay first. Sorting here is presentation: stored order and the domain
  history stay chronological (ADR-0006). Card and entity ordering are out of
  scope for this entry; I-015 covers the chart.
- **Dependencies:**
  - parked `google-sheets-source-of-truth` (the change this belongs to) — known
  - I-008 (invalid sheet rows tab may rely on row numbering) — known
  - ADR-0006 (domain history is chronological) — known
  - ADR-0004 (sheet layout is not part of the accepted decision while it stays
    `proposed`) — dependency unknown
- **Open questions:** insert-at-top or raw append plus a sorted view? Does the
  adapter own the layout at all, or is it the user's sheet? How do existing
  sheets migrate — do existing rows move on first write? Do formulas and ranges
  that point at rows shift correctly? Confirm that card, entity attributes and
  calendar stay unaffected (intended: yes).
- **Decision:** —

---

### I-015: Chart of period lengths and cycle lengths over time

- **Status:** idea
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
  (that change is parked). The native-statistics path is the lower-effort one
  and needs no new frontend dependency, but it draws a step series rather than
  one point per cycle.
- **Value:** users can see whether their cycles are regular and whether a
  prediction is plausible; the chart supports the "window, not a date" promise
  of BDR-0004 instead of hiding it behind a single number.
- **Constraints / conflicts:** the card change is parked, and BDR-0002 says the
  card ships with the integration, so a card chart inherits the parked work.
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
- **Dependencies:**
  - BDR-0004 (window, uncertainty and outlier rules) — known
  - BDR-0002 (the card ships with the integration) — known
  - parked `add-lovelace-card` — known
  - I-013 (configurable window size; whether the chart shows the prediction
    window or all history, and therefore whether it needs the same setting, is
    not decided) — dependency unknown
- **Open questions:** native statistics, a card chart, or both? How many cycles
  shown — all history or the prediction window? Plot out-of-range cycles with a
  marker instead of dropping them? Include the mean and the ±1σ band? Which
  entity carries the chart data, and when does a per-period value update?
- **Decision:** —
