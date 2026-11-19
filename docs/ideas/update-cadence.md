# Ideas: Coordinator Update Cadence and Manual Refresh

Theme: how often the coordinator recomputes cycle data, and how the user can
force a recomputation on demand instead of waiting for the next tick.

---

### I-012: Daily update instead of sub-hourly polling, plus a forced refresh

- **Status:** idea
- **Problem:** cycle data moves on a day scale — dates, the phase and the
  "days until" values roll over at midnight, which the code already reflects by
  keying the cached snapshot to the local date (`coordinator.py:425-433`) — yet
  the coordinator polls every 5 minutes by default and can be configured to at
  most every 60 minutes (`const.py:103-105`). The clamp lives in
  `config_flow.py:132-134` and the value is consumed as `update_interval` in
  `coordinator.py:110`, so a daily cadence cannot be configured at all. Every
  tick calls `read_all()` on the repository (`coordinator.py:188`,
  `coordinator.py:199`); with the Sheets repository that is a remote API read on
  every poll. The rest of the time it is needless CPU and repeated entity
  updates on values that only change at midnight. No sensor declares a
  `state_class`, so Home Assistant generates no long-term statistics from these
  polls today. There is also no user-triggered refresh: no `async_request_refresh`
  call and no refresh service exist, so a user who edited the sheet by hand,
  changed the system clock or timezone, or simply does not want to wait for the
  next tick has no documented way to recompute. `log_start` and `log_end` do
  republish data after a write (`services.py:105`, `services.py:119` calling
  `coordinator.async_set_updated_data`, `coordinator.py:472-476`), but neither
  re-reads the repository.
- **Idea:** let the cadence be daily — one refresh per day, aligned to local
  midnight rather than to setup time plus 24 hours, because the phase and the
  "days until" values roll over at midnight. Add a manual refresh: a
  `cycle_tracker.refresh` service and a button entity. Keep the existing service
  calls recalculating immediately — they already rebuild the snapshot after a
  write — and make that behavior explicit if it is kept.
- **Value:** much less background work and predictable update timing; the values
  change when the calendar day changes, not five minutes later; no waiting after
  a correction, a timezone change, or an edit made outside Home Assistant.
- **Constraints / conflicts:** settings live in the config entry (ADR-0011), so
  the interval and any new option belong there, not in integration storage. The
  coordinator stays an adapter around the domain (ADR-0005, ADR-0006).
  Changing the clamp is backward compatible for existing entries if the current
  default of 5 minutes is preserved. A midnight-aligned tick is not the same as
  a rolling 24-hour interval — and DST makes "every 24 hours" drift away from
  midnight twice a year, so the two options have different semantics. The
  integration has no midnight timer today: no `async_track_time_change` call
  exists, and the calendar only sorts and formats snapshot events
  (`calendar.py:85-90`). A daily tick means one scheduled entity update per day
  instead of up to 288 at the 5-minute default, which is the point — but a
  missed tick is then visible for a whole day. There is no `button` platform in
  the integration yet, so a button is a new platform, not an addition to an
  existing one.
- **Dependencies:**
  - ADR-0011 (the config entry owns settings) — known
  - ADR-0005 (pure domain, adapters at the edge) — known
  - ADR-0006 (explicit domain model contract) — known
  - ADR-0004 (Google Sheets as source of truth; its polling interval is still an
    open follow-up at `docs/adr/0004-google-sheets-source-of-truth.md:105`, so
    whether a daily tick is compatible with the Sheets adapter is unconfirmed)
    — dependency unknown
  - parked `google-sheets-source-of-truth` (a sync adapter would add its own
    polling pressure, and the parked change cannot be checked for cadence
    requirements) — dependency unknown
- **Open questions:** fixed daily cadence or configurable (for example hours
  1–24, or "daily at HH:MM")? Align to local midnight or keep a rolling
  interval? Should a stale snapshot — not refreshed for more than 24 hours — be
  flagged as an attribute? Should the midnight refresh be a coordinator timer or
  something the calendar/platform layer drives? Service plus button, or only the
  service? Should the button be disabled by default or marked diagnostic?
- **Decision:** —
