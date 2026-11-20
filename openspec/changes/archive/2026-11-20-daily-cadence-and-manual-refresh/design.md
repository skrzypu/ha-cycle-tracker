# Design

## Context

See `proposal.md` for motivation. The relevant current state:

- `CycleTrackerCoordinator` is a `DataUpdateCoordinator` built with
  `update_interval=timedelta(minutes=poll_minutes)` (`coordinator.py:112-119`).
  `_poll_interval_minutes()` reads the config entry and clamps to 1–60 minutes
  (`coordinator.py:153-168`); the same clamp is applied in the config and
  options flows (`config_flow.py:139-141`, `:448`, `:571-573`).
- The derived `snapshot` is cached by local date (`coordinator.py:431-442`) but
  rebuilt lazily when a reader notices the date change. Entities only publish
  new state when the coordinator publishes, so a date rollover by itself does
  not update the UI — a coordinator refresh event is required.
- `last_sync` and `sync_status` already exist (`coordinator.py:457-479`) but no
  sensor exposes them. Availability is `consecutive_failures < 3`
  (`coordinator.py:448-455`), independent of elapsed time.
- Services resolve their target entry through `_async_resolve_coordinator`
  (`services.py:59-92`). `log_start` and `log_end` call
  `async_set_updated_data(coordinator._data)` after a write (`services.py:105`,
  `:119`) — a local republish with no re-read.
- There is no `button` platform; `PLATFORMS` lists sensor, calendar and binary
  sensor (`const.py:8`).
- ADR-0011 puts settings in the config entry, ADR-0005/0006 keep the coordinator
  an adapter around the pure domain, and ADR-0004 makes the Sheet authoritative.

## Goals / Non-Goals

**Goals:**

- One Sheet read per local calendar day, at local midnight.
- An immediate, user-triggered re-read via both a service and a button, using
  one code path.
- An immediate re-read after every successful write.
- Surface the last successful read time and a stale indicator as sensor
  attributes.
- Leave availability semantics and the domain layer unchanged.

**Non-Goals:**

- Configurable HH:MM tick time, or any replacement for `poll_interval`.
- A diagnostics platform (I-017) or changes to the bundled card.
- Changing when entities are marked unavailable.

## Decisions

### 1. Midnight timer instead of a periodic interval

Register `async_track_time_change(hass, callback, hour=0, minute=0)` from the
coordinator and construct the base coordinator with `update_interval=None`. The
callback calls `coordinator.async_request_refresh()`, which performs a full
Sheet read and republish. The unsub callback is registered with
`entry.async_on_unload` so unload releases it.

- **Why:** the derived values roll over at local midnight, and
  `async_track_time_change` follows local time across DST. A rolling
  `timedelta(days=1)` anchored at setup drifts away from midnight twice a year.
- **Alternatives rejected:** driving the tick from the calendar or sensor
  platform (the coordinator owns refresh and listener notification); keeping a
  short interval that reads the cache (would retain the polling cost the change
  removes).
- `async_config_entry_first_refresh()` still runs at setup with no
  `update_interval`, so a restart self-heals a missed midnight tick.

### 2. Remove the poll-interval setting rather than repurpose it

Drop `CONF_POLL_INTERVAL` from the sheet step, options step, clamp helper,
constants and translations. Existing entries keep an unused key; no data
migration is needed because unknown config keys are ignored.

- **Why:** a minutes setting cannot express "daily at midnight" without an
  ambiguous type change (an existing `5` would mean either 5am or 5 minutes).
- **Alternative rejected:** reinterpret as hours between reads — ambiguous
  around DST and no longer midnight-aligned.

### 3. One refresh path shared by service and button

Add `SERVICE_REFRESH = "refresh"`. Its schema contains only the target fields;
the handler resolves the coordinator with `_async_resolve_coordinator` and calls
`async_request_refresh()`. A new `button` platform entity implements
`async_press()` by calling that service with itself as the target. It is enabled
by default and has no `EntityCategory`.

- **Why:** the service is needed for automations and voice, the button makes the
  escape hatch discoverable, and routing the button through the service keeps
  target resolution and refresh behavior in one place.

### 4. Writes re-read instead of republishing from memory

Replace the two `async_set_updated_data` calls in `services.py` with
`await coordinator.async_request_refresh()` after a successful write. The write
methods already invalidate the snapshot; the refresh then re-reads and
publishes once.

- **Why:** chosen to keep the Sheet authoritative even when another writer
  changed it concurrently, at the cost of one extra API read per write.
- The coordinator's request-refresh debouncer may collapse two very rapid writes
  into one re-read; that still satisfies "re-read after a write".
- `last_sync` therefore means *last successful contact with the Sheet*, updated
  by the midnight read, manual refreshes and write-triggered re-reads. The
  attribute description must say so.

### 5. Stale attribute on the statistics sensor

Add `last_sync` and `is_stale` attributes to the existing statistics sensor,
which already carries diagnostics-like values such as `usable_cycle_count` and
`warnings`. `is_stale` is true when `last_sync` is absent or its local date is
before yesterday.

- **Why:** a calendar-day rule tolerates the 23- and 25-hour DST days and a
  single missed midnight, unlike a fixed 24-hour threshold. It also leaves
  availability logic untouched, as required.

## Risks / Trade-offs

- **[Missed midnight]** → HA not running at 00:00 produces no read that day.
  Mitigation: setup always performs a first refresh; the stale attribute makes
  the gap visible; manual refresh is always available.
- **[Extra API calls on writes]** → a write now costs a write plus a read.
  Accepted; the debouncer limits bursts.
- **[Write succeeds, re-read fails]** → the read-through cache fallback and
  repair issue are used even though the write persisted. Mitigation: correct
  data is retained; the next midnight or manual read heals it.
- **[DST]** → local midnight stays aligned but day length varies. Mitigation:
  calendar-day-based stale rule.
- **[Stale config key]** → entries retain `poll_interval`. Mitigation: ignored
  on read and absent from the UI; no behavior depends on it.
- **[Spec wording]** → the old availability sentence was time-based and never
  matched the count-based implementation; it is now documented as the
  consecutive-failure rule. I-017 may revisit visibility later.

## Migration Plan

No stored-data migration: the old `poll_interval` key is left in place and
ignored. Deployment is a normal integration reload. Rollback restores the
previous scheduling code without data loss. Bump the patch version per ADR-0016.
