# Tasks

## 1. Resolution

- [x] 1.1 Add a helper that resolves a `ServiceCall` to a `CycleTrackerCoordinator` through `async_extract_entity_ids` plus the entity registry, with a single-entry fallback and a `ServiceValidationError` for a foreign target, an empty target or an ambiguous setup
- [x] 1.2 Replace both `call.config_entry.entry_id` lookups with the helper

## 2. Schemas and metadata

- [x] 2.1 Add optional `entity_id`, `device_id` and `area_id` to both service schemas so a call carrying a target passes validation
- [x] 2.2 Add a target selector for the integration's entities to `services.yaml`

## 3. Behaviour

- [x] 3.1 Keep the `success`/`message` response shape for both services
- [x] 3.2 Reject `log_end` when the date precedes the latest start and leave stored data unchanged

## 4. Tests

- [x] 4.1 Drive `log_start` through `hass.services.async_call` with no target and assert the stored row plus the returned response
- [x] 4.2 Call `log_start` and `log_end` with an entity target and assert the period is opened and then closed
- [x] 4.3 Assert a foreign target and a two-entry call without a target raise `ServiceValidationError` and record nothing
- [x] 4.4 Assert `log_end` before the start reports failure and leaves the stored row unchanged

## 5. Verification

- [x] 5.1 `pytest tests/adapters -q` passes
- [x] 5.2 `pre-commit run --all-files` passes
- [x] 5.3 `openspec validate fix-logging-services --strict` reports valid
