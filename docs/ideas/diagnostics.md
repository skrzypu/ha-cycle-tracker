# Ideas: Diagnostics and Data Quality

Theme: showing why a prediction looks the way it does, and giving support a
snapshot without asking for logs.

---

### I-017: A diagnostics view — last refresh, excluded cycles, gaps and data quality

- **Status:** idea
- **Problem:** the reasons behind a prediction are spread thin. The statistics
  sensor carries `usable_cycle_count` and a list of warnings
  (`sensor.py:333-339`), the prediction sensors carry the window and confidence
  (`sensor.py:187-201`), but nothing says when the data was last refreshed, which
  cycles were excluded as outliers, where a gap truncated the window, or why the
  prediction is `unknown`. There is no Home Assistant diagnostics platform in the
  integration — only `repairs.py`, which reports Google Sheets problems — so a
  support request has nothing downloadable to attach.
- **Idea:** two layers. (a) A `diagnostics.py` platform exposing a redacted dump
  of stored periods, the usable window, exclusions, gaps and the relevant
  settings. (b) A human-facing surface: attributes on the statistics sensor
  and/or a small diagnostic sensor with the last-refresh timestamp and the list
  of excluded cycles and gaps. Cross-reference I-008 (invalid sheet rows) and
  I-012 (daily cadence); this entry is about visibility, not about changing
  either behaviour.
- **Value:** users can see why the integration says "unknown" or why a value
  changed; maintainers get a structured snapshot instead of asking the user to
  enable debug logging and paste log lines.
- **Constraints / conflicts:** diagnostics output can leak sensitive health data,
  so HA's redaction support must be used and every field reviewed (ADR-0001
  keeps processing local — nothing may be uploaded by this feature). The domain
  already produces warnings for excluded cycles and gaps, so most of the data
  exists; adding a platform is an adapter change under ADR-0005. Avoid turning
  diagnostics into a second, conflicting API: the statistics sensor stays the
  source of user-facing aggregates.
- **Dependencies:**
  - I-012 (a last-refresh timestamp has to come from the coordinator/cadence
    change) — dependency unknown
  - I-008 (invalid sheet rows tab; adjacent data-quality surface) — known
  - ADR-0006 (domain history and warnings) — known
  - ADR-0001 (local-only, sensitive data) — known
  - ADR-0005 (adapters at the edge) — known
- **Open questions:** diagnostics platform only, or also entities? Which fields
  are redacted by default? Does the stale flag from I-012 live here or on the
  statistics sensor? Should an `unknown` prediction also raise a repair issue,
  or is that noise for new users? Should excluded cycles be listed by ID, date,
  or both?
- **Decision:** —
