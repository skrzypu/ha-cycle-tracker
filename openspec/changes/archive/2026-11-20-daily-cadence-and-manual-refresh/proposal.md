# Proposal

## Why

Cycle data changes on a day scale: phase and "days until" values roll over at
local midnight, yet the coordinator polls the Google Sheet every five minutes
by default and cannot be configured beyond 60 minutes. Each poll performs a
remote read on values that cannot have changed, and there is no way for a user
to force a recomputation after editing the Sheet by hand or changing the system
clock or timezone. I-012 in the idea backlog records this problem.

## What Changes

- **BREAKING**: replace the configurable 1–60 minute poll interval with one
  Sheet read per day, aligned to local midnight. Remove `poll_interval` from
  the config flow and options flow; ignore the stale key in existing entries.
- Drive the daily read with a local-midnight time-change listener rather than a
  rolling 24-hour interval, so values roll over when the calendar day does and
  the schedule does not drift across DST.
- Add a `cycle_tracker.refresh` service that requests an immediate coordinator
  refresh, using the existing entity/device/area target resolution.
- Add a refresh button entity (new `button` platform), enabled by default and
  routed through the same service, so the escape hatch is discoverable in the
  UI.
- Make writes request an immediate re-read of the Sheet after every successful
  `log_start` / `log_end`, instead of republishing from the in-memory model
  only. The explicit `async_set_updated_data` calls in the service handlers are
  removed so a write publishes once.
- Expose the time of the last successful Sheet read (and a stale indicator) as
  an attribute on an existing sensor. Availability semantics are unchanged.
- Amend the archived `sheet-sync` freshness requirement, whose configurable
  five-minute interval no longer describes the system.

Out of scope: a diagnostics platform (I-017), a configurable HH:MM tick time,
changing availability thresholds, and changes to the bundled card.

## Capabilities

### New Capabilities

None. Manual refresh is a freshness behavior of the existing `sheet-sync`
capability; a separate capability would duplicate that boundary.

### Modified Capabilities

- `sheet-sync`: replace the configurable five-minute freshness interval with a
  daily midnight read plus an on-demand `refresh` service and button; state
  that successful writes request an immediate re-read; expose the last
  successful sync time.
- `cycle-logging-services`: extend the service lifecycle and target-resolution
  requirements to the new `refresh` service.
- `integration-lifecycle`: the unload requirement must cover releasing the
  midnight timer rather than only a periodic refresh timer.

## Impact

- Code: `coordinator.py` (schedule, timer registration, `last_sync` semantics),
  `config_flow.py` and `const.py` (setting removal), `services.py` (new
  handler, write-path re-read), new `button.py`, `__init__.py` (`PLATFORMS`),
  `sensor.py` (attribute), `strings.json` and `translations/{en,pl}.json`.
- Tests: coordinator scheduling, config/options flow, services, button entity,
  and the persistence E2E flow.
- HA APIs: `async_track_time_change`, `DataUpdateCoordinator` with
  `update_interval=None` and `async_request_refresh()`.
- Decisions/dependencies: ADR-0004 (Sheet is source of truth), ADR-0005 and
  ADR-0006 (adapter around the pure domain), ADR-0011 (config entry owns
  settings), ADR-0016 (spec changes bump the patch version). Feeds I-017, which
  consumes the exposed last-sync timestamp.
