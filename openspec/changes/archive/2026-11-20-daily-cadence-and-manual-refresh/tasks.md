# Tasks

## 1. Coordinator scheduling

- [x] 1.1 Construct `CycleTrackerCoordinator` with `update_interval=None` and register an `async_track_time_change(hass, ..., hour=0, minute=0)` callback that calls `async_request_refresh()`; register its unsub with `entry.async_on_unload`. Verify with a coordinator unit test that invoking the registered midnight callback triggers one repository read and a republish, and that unloading releases the timer.
- [x] 1.2 Remove `_poll_interval_minutes()` and the poll-interval imports/clamp from `coordinator.py`. Verify that coordinator tests no longer reference `CONF_POLL_INTERVAL` and that setting the stale option has no effect on scheduling.

## 2. Configuration surface

- [x] 2.1 Remove `CONF_POLL_INTERVAL` from the sheet step, options step, clamp helper and defaults in `config_flow.py`, and delete the constant and MIN/MAX/DEFAULT values from `const.py`. Verify that config-flow and options-flow tests assert the field is absent and that existing entries with the stale key load unchanged.
- [x] 2.2 Remove the `poll_interval` label from `strings.json` and `translations/{en,pl}.json`. Verify no translation key remains and the config-flow schema validation passes.

## 3. Refresh service

- [x] 3.1 Add `SERVICE_REFRESH = "refresh"` and register a `refresh` handler whose schema carries only the target fields, resolves the coordinator with `_async_resolve_coordinator`, and calls `await coordinator.async_request_refresh()`. Verify with service tests that a call on a single entry and a call targeted at a Cycle Tracker entity both re-read the sheet, a foreign or ambiguous target is rejected, and unload removes the service.

## 4. Button platform

- [x] 4.1 Add `button.py` with a refresh button entity whose `async_press()` calls the `refresh` service with itself as target; add `Platform.BUTTON` to `PLATFORMS`. Verify with a platform test that the entity is created enabled by default, that pressing it triggers exactly one coordinator re-read, and that unloading removes the platform.

## 5. Write-path re-read

- [x] 5.1 Replace the `async_set_updated_data(coordinator._data)` calls after successful `log_start` and `log_end` writes with `await coordinator.async_request_refresh()`. Verify with service tests that a successful write re-reads the sheet and publishes once, that a failed write requests no re-read, and that the last-sync timestamp updates only after a successful re-read.

## 6. Freshness attributes

- [x] 6.1 Add `ATTR_LAST_SYNC` and `ATTR_IS_STALE` constants and expose them on the existing statistics sensor, with staleness defined by local calendar day (stale when `last_sync` is absent or its local date is before yesterday). Verify with sensor tests using a frozen clock that the attributes are present, `is_stale` is false on the day of and day after a read, and true for older or absent timestamps; availability assertions are unchanged.

## 7. Integration verification

- [x] 7.1 Bump the patch version per ADR-0016 and verify the manifest/version consistency test passes.
- [x] 7.2 Update the persistence E2E flow so an external sheet edit is picked up through a manual refresh rather than a five-minute poll, and verify the E2E suite passes.
- [x] 7.3 Run `pre-commit run --all-files` and verify it exits 0 with no ruff, ruff-format, mypy or pytest failures.
