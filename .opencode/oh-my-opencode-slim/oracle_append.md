## Project-Specific Oracle Rules for ha-cycle-tracker

### Architecture Decision Records (ADRs)
Document all major decisions in `docs/adr/` with format:
```
001-python-ha-component-structure.md
002-prediction-algorithm-selection.md
003-data-persistence-strategy.md
004-testing-strategy.md
005-future-ffi-readiness.md
```

### Key Architectural Decisions (Pre-seeded)

#### ADR 001: Python HA Component - Native Custom Component
- **Decision**: Standard HA custom component in `custom_components/cycle_tracker/`
- **Rationale**: 
  - Native HA integration (config flow, sensors, calendar, services)
  - HACS distribution standard
  - Direct access to HA APIs (storage, coordinator, websocket)
- **Alternatives Considered**: AppDaemon (separate runtime), MQTT bridge (complexity), REST API (latency)

#### ADR 002: Prediction Algorithms - Pluggable Strategies
- **Decision**: Strategy pattern with ArithmeticMean, WMA implementations in coordinator
- **Rationale**: 
  - OCP: Add new methods (ML, Bayesian) without changing domain
  - Configurable per user (some prefer simple average)
  - Testable in isolation
- **Default**: WMA with weights [0.5, 0.3, 0.2] for last 3 cycles

#### ADR 003: Data Persistence - HA Storage
- **Decision**: HA `Store` persists period history; coordinator holds current cycle in memory
- **Rationale**: 
  - HA handles backup/restore, migration, encryption
  - Simple in-memory calculations, no persistence complexity
  - Coordinator reloads history on startup
- **Sync**: `log_start`/`log_end` services → HA Store → Coordinator refresh

#### ADR 004: Testing - Contract-First with Property Tests
- **Decision**: Shared JSON Schema for future FFI, property tests for algorithms, contract tests in CI
- **Rationale**: 
  - Catches FFI drift early (when FFI is added)
  - Property tests find edge cases in statistics
  - Unit + integration tests for HA component
- **Gates**: Pre-commit + CI must pass all test suites

#### ADR 005: Future FFI Readiness
- **Decision**: Keep JSON schema (`specs/ffi-contract.schema.json`) for potential future KMP/FFI
- **Rationale**: 
  - If performance becomes issue, can extract algorithms to KMP
  - Schema already defined, contract tests ready
  - Minimal migration effort

### Review Criteria (Code Review)

#### For Python Code (@python-ha-component output)
- [ ] Type hints everywhere (mypy strict passes)
- [ ] Async/await for all HA APIs
- [ ] Library load failure → warning + graceful degradation (not crash)
- [ ] Config flow uses HA selectors, proper validation
- [ ] Sensors extend `SensorEntity`, Calendar extends `CalendarEntity`
- [ ] Services registered via `services.yaml` + `async_register_admin_service`
- [ ] `pytest tests/` passes with mocked dependencies

#### For Future FFI Boundary
- [ ] JSON Schema in `specs/ffi-contract.schema.json` matches both sides
- [ ] Version field in all responses (`ffi_version: 1`)
- [ ] Error codes documented (0=success, -1=invalid handle, -2=serialization error)
- [ ] Memory: KMP owns handle lifecycle, Python calls `destroy` on unload

#### For Tests (@test-engineer output)
- [ ] Unit tests for every algorithm (Python)
- [ ] Property tests for statistical invariants (hypothesis)
- [ ] Contract tests validate JSON against schema
- [ ] Integration tests with HA test instance
- [ ] E2E tests cover user flows (log start → predict → log end)
- [ ] Fixtures shared via `tests/fixtures/*.json`

### Simplification Reviews (per `simplify` skill)
- **YAGNI Check**: Is this abstraction needed now? (e.g., plugin system for predictions)
- **Complexity Budget**: Cyclomatic complexity <10 per function
- **Duplication**: DRY across domain models
- **Dependencies**: Minimize - no heavy libs for simple tasks

### Debugging Guidance (per `systematic-debugging`)
- **Prediction Wrong**: Verify input cycles fed to coordinator match HA storage
- **Sensor Stale**: Check coordinator update interval, calculation success
- **Config Flow Broken**: HA version compatibility, selector API changes
- **Storage Issues**: Check Store key, version migration

### Escalation Triggers
- HA API breaking change → `@api-researcher` + `@python-ha-component` migration plan
- Algorithm accuracy complaints → `@python-ha-component` review math
- Performance issues (calculation latency) → profile, consider caching
- HACS validation failures → `@test-engineer` + `@python-ha-component` fix