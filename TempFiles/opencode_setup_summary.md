# ha-cycle-tracker - OpenCode Configuration Summary

**Date**: 2026-10-01  
**Project**: Home Assistant Menstrual Cycle Tracker (KMP + Python)  
**Status**: Configuration complete, ready for implementation

---

## ✅ COMPLETED - OpenCode Configuration

### 1. Project Configuration (`opencode.json`)
- **7 specialized subagents** with clear delegation rules:
  - `kmp-architect` (oracle) - KMP architecture, Gradle, FFI strategy
  - `kmp-implementer` (fixer) - Domain, algorithms, FFI exports, unit tests
  - `python-ha-component` (fixer) - HA custom component, config flow, sensors, FFI bridge
  - `test-engineer` (fixer) - E2E tests, contract tests, pre-commit, CI
  - `api-researcher` (librarian) - HA API, KMP/Native, Python FFI, HACS research
  - `code-explorer` (explorer) - Fast cross-language code navigation
  - `design-reviewer` (designer) - Lovelace card, config flow, dashboard UX
  - `orchestrator-coach` (oracle) - Meta-coaching for delegation patterns

- **20 skills enabled** in config (need installation via script)
- **Hooks configured**: pre-commit runs all checks, pre-push blocked
- **Permissions**: Scoped to project file types (Kotlin, Python, YAML, etc.)
- **Environment**: GRADLE_OPTS, PYTHONPATH set

### 2. Project-Local oh-my-opencode-slim Config (`.opencode/oh-my-opencode-slim.json`)
- Tuned models/skills per agent for this project
- Orchestrator gets orchestration skills
- Fixer gets TDD + verification skills
- Designer gets mobile design + browser automation
- Tester gets webapp-testing + playwright-best-practices

### 3. Agent Prompt Append Files (`.opencode/oh-my-opencode-slim/*_append.md`)
| File | Purpose |
|------|---------|
| `orchestrator_append.md` | Delegation rules, parallel patterns, FFI discipline, verification gates |
| `fixer_append.md` | KMP domain/FFI structure, Python component structure, code quality rules |
| `tester_append.md` | Test strategy, property tests, contract testing, pre-commit config, CI pipeline |
| `librarian_append.md` | Research domains with official sources, quality filters |
| `designer_append.md` | Lovelace card specs, accessibility, theming, responsive breakpoints |
| `oracle_append.md` | ADRs, review criteria, simplification, debugging guidance |
| `explorer_append.md` | Search patterns, cross-language traces, file ownership map |

### 4. Key Architectural Decisions Documented
- **FFI Strategy**: cbindgen (Kotlin) + ctypes (Python) with JSON serialization
- **Persistence**: HA Store + KMP in-memory per session
- **Algorithms**: Pluggable `PredictionStrategy` (ArithmeticMean, WMA)
- **Testing**: Contract-first with shared JSON Schema, property tests, native FFI tests

### 5. Installation Script Created
- `install-skills.sh` - Installs all 20 declared skills via Skills CLI

---

## 📋 TODO - Before Starting Implementation

### Immediate (Run Once)
- [ ] **Run skills installation**: `./install-skills.sh` (requires Node.js/npx)
- [ ] **Restart OpenCode** for oh-my-opencode-slim changes to take effect
- [ ] **Verify skills installed**: `ls ~/.config/opencode/skills/` should show all 20 skills

### Phase 1: Foundation (Can run in parallel)
- [ ] **KMP Project Setup** → `@kmp-architect`
  - Gradle multi-project structure (`cycle-tracker-core` module)
  - Kotlin 2.0.20, KMP plugin, linuxX64 + JVM targets
  - cbindgen configuration for FFI headers
  - Serialization setup (kotlinx.serialization)
  
- [ ] **Python HA Component Skeleton** → `@python-ha-component`
  - `custom_components/cycle_tracker/` structure
  - `manifest.json`, `hacs.json`, `services.yaml`
  - Config flow with 3 steps (basic, preferences, notifications)
  - Empty sensor/calendar entities

- [ ] **Test Infrastructure** → `@test-engineer`
  - `.pre-commit-config.yaml` with all hooks
  - `pytest` + `pytest-homeassistant-custom-component` setup
  - `kotest` + `kotest-property` for KMP
  - Shared fixtures in `tests/fixtures/`
  - Contract validation script (`scripts/validate_contract.py`)
  - GitHub Actions CI (`.github/workflows/ci.yml`)

### Phase 2: Core Implementation (Parallel lanes)
- [ ] **KMP Domain & Algorithms** → `@kmp-implementer`
  - `Cycle`, `PeriodEntry`, `CyclePhase`, `PredictionResult`, `Statistics`
  - `PredictionStrategy` interface + `ArithmeticMeanStrategy`, `WeightedMovingAverageStrategy`
  - `StandardDeviationCalculator`
  - Property tests for statistical invariants

- [ ] **KMP FFI Layer** → `@kmp-implementer`
  - `@CName` exports: `ct_create`, `ct_destroy`, `ct_add_period`, `ct_predict`, `ct_get_stats`
  - JSON serialization for FFI boundary
  - Opaque handle memory management
  - Native tests (`linuxX64Test`) loading `.so`

- [ ] **Python FFI Bridge** → `@python-ha-component`
  - `ffi_bridge.py` with ctypes wrapper
  - Library loading from HA config directory
  - Executor pattern for non-blocking calls
  - Error handling → HA warnings

- [ ] **Python Coordinator & Sensors** → `@python-ha-component`
  - `DataUpdateCoordinator` with periodic updates
  - `CycleDaySensor`, `CyclePhaseSensor`, `NextPeriodDateSensor`
  - `MenstrualCycleCalendar` entity
  - Services: `log_start`, `log_end` → HA Store + KMP

### Phase 3: UI & Polish
- [ ] **Lovelace Card** → `@design-reviewer` + `@fixer`
  - TypeScript/Lit custom card
  - Phase indicator, countdown, one-tap logging
  - Responsive, accessible, HA theming

- [ ] **Config Flow UX** → `@design-reviewer` + `@python-ha-component`
  - 3-step wizard with selectors
  - Validation, progress, helpful hints

### Phase 4: Verification & HACS
- [ ] **Contract Validation** → `@test-engineer`
  - Shared JSON Schema (`specs/ffi-contract.schema.json`)
  - Both sides validate on every FFI call
  - CI gate on schema compliance

- [ ] **HACS Preparation** → `@python-ha-component`
  - Version tagging, release workflow
  - Documentation (README, CHANGELOG)

---

## 🚀 HOW TO START NEW SESSION

```bash
cd /home/tomek/workspace/ha-cycle-tracker

# 1. Install skills (first time only)
./install-skills.sh

# 2. Restart OpenCode

# 3. Start with orchestrator - it will know all subagents and rules
# Example first task:
# "Use @kmp-architect to set up the Gradle KMP project structure with linuxX64 target and cbindgen for FFI"
```

---

## 📁 KEY FILES REFERENCE

| File | Purpose |
|------|---------|
| `opencode.json` | Main project config, subagents, skills, hooks |
| `.opencode/oh-my-opencode-slim.json` | Agent model/skill tuning |
| `.opencode/oh-my-opencode-slim/*_append.md` | Agent-specific rules |
| `install-skills.sh` | Skills installation script |
| `TempFiles/product_roadmap_ha_cycle_tracker.md` | Original product roadmap |
| `specs/` | (To create) Open Spec Kit specs + FFI contract schema |

---

## ⚠️ IMPORTANT RULES (Enforced by Config)

1. **No commits/pushes without explicit user permission** (pre-push hook blocks)
2. **Pre-commit must pass** before any commit (all tests, lint, contract validation)
3. **Use subagents** - don't implement directly when a specialist exists
4. **Parallel dispatch** - independent lanes run simultaneously
5. **Verification required** - every task ends with evidence (test output, contract validation)
6. **FFI contract discipline** - both sides validate against shared JSON Schema