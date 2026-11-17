## ha-cycle-tracker — routing and gates

Pure-Python Home Assistant integration. Domain in `custom_components/cycle_tracker/domain/`,
adapters in the sibling modules.

Delegate by role:
- implementation (config flow, sensors, calendar, services, algorithms) → @fixer
- tests (pytest, contracts, E2E, pre-commit) → @test-engineer
- research (HA API, component patterns, HACS) → @librarian
- codebase navigation / search → @explorer
- UI/UX (config flow, Lovelace card) → @designer
- architecture, risk, debugging, review → @oracle
- delegation meta-coaching → @orchestrator-coach
- "is the agent/config documentation still true?" → @agent-auditor

## OpenSpec routing

The orchestrator owns the OpenSpec flow but delegates each operation to a specialist instead of
running it inline. `explore` is the exception — it is an in-session conversation, not delegatable.

- `/opsx-explore`  → orchestrator (interactive thinking; reads code, never implements)
- `/opsx-propose`  → @oracle (planning/design: proposal, specs, design, tasks)
- `/opsx-apply`    → @fixer (implements the tasks; @test-engineer writes the tests)
- `/opsx-verify`   → @oracle (advisory review of implementation against the artifacts)
- `/opsx-sync`     → @fixer (mechanical delta→main-spec merge; runs inside archive)
- `/opsx-archive`  → @fixer (status, sync, move change to archive — a regular model, not oracle)

Posture: delegate anything that matches a specialist role — never implement, test, design, or
research inline. The orchestrator plans lanes, dispatches in parallel, reconciles results, and
runs the single full verification gate after writers finish.

Gates: `pre-commit run --all-files` must pass (ruff, ruff-format, mypy, pytest).
Never commit or push without explicit user permission.
Keep subagent replies concise: paths, line references and diffs — not full-file pastes.
