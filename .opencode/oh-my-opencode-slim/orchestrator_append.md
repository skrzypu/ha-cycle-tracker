## Project-Specific Orchestrator Rules for ha-cycle-tracker

### Architecture Context
- **Python HA Component** (`custom_components/cycle_tracker/`): Config flow, sensors, calendar, services, prediction algorithms (pure Python)
- **No KMP/FFI** - all logic implemented in Python for simplicity and maintainability

### Delegation Rules

#### ALWAYS delegate to subagents for:
- **Python HA Component** → `@python-ha-component` (config flow, sensors, calendar, services, algorithms)
- **Testing** → `@test-engineer` (pytest, contract tests, pre-commit, CI)
- **Research** → `@api-researcher` (HA API, Python HA custom component patterns, HACS)
- **Code Navigation** → `@code-explorer` (symbol search, call graphs, test files)
- **UI/UX** → `@design-reviewer` (Lovelace card, config flow, dashboard, accessibility)
- **Orchestration Coaching** → `@orchestrator-coach` (delegation patterns, parallel dispatch, branch finishing)

#### NEVER delegate to subagents for:
- One-line edits (<20 lines, single file)
- Simple questions you can answer directly
- Trivial file reads

### Parallel Dispatch Patterns
- **Independent lanes**: `@python-ha-component` (sensors) + `@python-ha-component` (calendar) can work in parallel
- **Research + Implementation**: `@api-researcher` runs first, then implementation agents use findings
- **Test + Implementation**: `@test-engineer` writes contract tests first (TDD), then implementers make them pass

### Contract Discipline
- Shared JSON Schema (`specs/ffi-contract.schema.json`) for any future FFI needs
- `@test-engineer` owns contract validation in CI

### Verification Gates (from skills)
- **test-driven-development**: Write failing test first (Python: pytest)
- **verification-before-completion**: Every task ends with evidence (test output, contract validation, lint pass)
- **systematic-debugging**: Hypothesis → test → verify loop for any bug
- **writing-plans + executing-plans**: Multi-step work gets a plan with checkpoints
- **subagent-driven-development**: Use specialized agents, not general implementation
- **dispatching-parallel-agents**: Split independent work across agents
- **requesting-code-review**: Prepare self-review before marking done
- **finishing-a-development-branch**: Tests pass, commit message, PR description, review request

### Pre-commit Requirements
- `pre-commit run --all-files` MUST pass (configured in hook)
- Includes: Python tests (pytest), contract validation, lint (ruff, mypy)
- No commits without explicit user permission
- No pushes without explicit user permission

### Cost/Quality Model Assignment
- **High judgment, low volume**: `oracle` (nemotron-3-ultra-free, high) - architecture, debugging, review
- **High volume, mechanical**: `fixer` (space-bunny-free, high) - implementation, tests
- **Research**: `librarian` (longcat-2.5-preview-free) - external docs, API lookup
- **Code search**: `explorer` (longcat-2.5-preview-free) - fast codebase nav
- **Design**: `designer` (space-bunny-free, medium) - UI/UX, Lovelace card
- **Orchestration**: `orchestrator` (nemotron-3-ultra-free, high) - coordination, planning

### Project-Specific Conventions
- **Clean Code**: Small functions, meaningful names, no magic numbers
- **SOLID**: SRP per algorithm, OCP via PredictionStrategy, LSP for phases, ISP for interfaces, DIP for storage
- **Modular**: `coordinator`, `sensor`, `calendar`, `config_flow`, `services` modules
- **Type Safety**: Python type hints (mypy strict)
- **Error Handling**: HA warnings (not crashes), storage failures → graceful degradation
- **Async**: All HA APIs async/await
- **Privacy**: Local-only, no cloud, no telemetry